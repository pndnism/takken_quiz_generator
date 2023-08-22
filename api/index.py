from fastapi import FastAPI, HTTPException, Depends, status, Request, Response
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import models.database as database
from models.models import Base, User, Law, get_db, Quiz
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from kanjize import number2kanji
import random
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from pydantic_settings import BaseSettings
from sqlalchemy import text
import openai
import logging
import bcrypt
import jwt
from datetime import datetime, timedelta
from typing import List
from jwt.exceptions import InvalidTokenError, ExpiredSignatureError
import json
from sqlalchemy.exc import IntegrityError

logging.basicConfig(level=logging.INFO)


app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "https://takken-quiz-generator-z22o.vercel.app", "https://takken-quiz-generator-z22o*.vercel.app"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class Settings(BaseSettings):
    SECRET_KEY: str = "09d25e094faa6ca2556c818166b7a9563b93f7099f6f0f4caa6cf63b88e8d3e7"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30


settings = Settings()


class HTTPBearerWithCookie(HTTPBearer):
    def __init__(self, auto_error: bool = True):
        super(HTTPBearerWithCookie, self).__init__(auto_error=auto_error)

    async def __call__(self, request: Request):
        authorization: str = request.cookies.get("access_token")
        logging.info(f"Access token: {authorization}")
        if not authorization:
            logging.warning("No access token found in cookie")
            raise HTTPException(status_code=401, detail="Invalid token")
        return HTTPAuthorizationCredentials(scheme="Bearer", credentials=authorization.replace("Bearer ", ""))


oauth2_scheme = HTTPBearerWithCookie()


def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))


def get_user(db: Session, username: str):
    return db.query(User).filter(User.username == username).first()


class UserRegister(BaseModel):
    username: str
    password: str


class UserLogin(BaseModel):
    username: str
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    username: str = None


class QuizCreate(BaseModel):
    question_text: str
    options: List[str]
    correct_choice: int
    user_answer: int = None


class QuizRequest(BaseModel):
    number_of_questions: int
    api_key: str


@app.post("/api/register")
def register(user: UserRegister, db: Session = Depends(get_db)):
    hashed_password = bcrypt.hashpw(user.password.encode('utf-8'), bcrypt.gensalt())
    new_user = User(username=user.username, password=hashed_password.decode('utf-8'))
    db.add(new_user)
    try:
        db.commit()
    except Exception as e:
        db.rollback()
        # ここでエラーメッセージをログに出力します
        print(f"Error detail: {str(e)}")
        raise HTTPException(status_code=400, detail="Username already exists")
    return {"message": "User registered successfully!"}


def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
    logging.info(f"credentials: {credentials}")
    token = credentials.credentials
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=settings.ALGORITHM)
        username: str = payload.get("sub")
        logging.info(f"username: {username}")
        if username is None:
            raise credentials_exception
    except (InvalidTokenError, ExpiredSignatureError):
        raise HTTPException(status_code=401, detail="Token has expired or is invalid. Please re-login.")
    user = db.query(User).filter(User.username == username).first()
    if user is None:
        raise credentials_exception
    logging.info(f"current_user: {user}")
    return user


@app.post("/api/generate-quiz")
async def generate_quiz(request: QuizRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    number_of_questions = request.number_of_questions
    api_key = request.api_key
    # APIキーの検証（必要に応じて）
    if not validate_api_key(api_key):
        raise HTTPException(status_code=400, detail="Invalid API Key")
    
    # database.pyからDATABSE_URLを取得
    engine = create_engine(database.DATABASE_URL)
    input_text = ""
    attempts = 0
    max_attempts = 5  # 任意の再試行回数を設定

    while not input_text and attempts < max_attempts:
        article_numbers = random.sample(range(1, 87), 2)
        article_numbers = [number2kanji(article_number) for article_number in article_numbers]
        article_numbers = [f"第{article_number}条" for article_number in article_numbers]
        article_numbers_for_query = ",".join(['\'' + article_number + '\'' for article_number in article_numbers])
        
        with engine.connect() as conn:
            query = text(f"""
                SELECT sentense_text
                FROM laws
                WHERE article_title in ({article_numbers_for_query})
            """)
            result = conn.execute(query)
            input_text = " ".join([row[0] for row in result.fetchall()])

        attempts += 1
        logging.info(f"input_text: {input_text}")
        # token（文字数）が10000字を超えている場合、input_textを10000字までに切り詰める
        if len(input_text) > 10000:
            input_text = input_text[:2000]
        input_text = input_text[:2000]

    if not input_text:
        raise HTTPException(status_code=500, detail="Failed to retrieve random article text")

    # openaiのchatgpt apiを呼び出して、生成された問題をjson形式で返す
    questions = call_chatgpt_api(api_key, input_text, number_of_questions)
    logging.info(questions)

    # 生成されたクイズの情報をデータベースに保存
    for quiz in questions:
        new_quiz = Quiz(
            user_id=current_user.id,  # この情報はどこから取得するかを確認する必要があります
            question_text=quiz["question_text"],
            options=json.dumps(quiz["options"]),
            correct_choice=quiz["correct_choice"],
            created_at=datetime.now(),
            # user_answerはnullで保存
        )
        db.add(new_quiz)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()

    return {"quizzes": questions}


def validate_api_key(api_key: str) -> bool:
    # ここでAPIキーの基本的な検証を行います。例えば、キーの長さをチェックするなど。
    # 必要に応じて具体的な検証内容を追加/修正してください。
    return len(api_key) > 20  # 例: キーの長さが20文字以上であるかどうかを確認


def call_chatgpt_api(api_key: str, input_text: str, number_of_questions: int):
    # プロンプトを作成
    prompt = f"""
    以下のインプットに基づいて、4択の文章から正しい文章を選択する4択の文章を{number_of_questions}問作成してください。選択肢の文章はインプットの一部をそのまま取り出すのではなく、インプットから得られる情報に応じて下記例文のような形式の文章を生成してください。正解選択肢はランダムに配置し、各問題の正解の選択肢番号と、それが正解になる理由の解説、またその他の選択肢が間違いである理由の解説も出力してください。
    また、正解や間違いの理由に「文章／インプットに記載／記述されているように」に類する記述は書かないでください。

    選択肢例文: 「農地の賃貸借および使用貸借は、その登記がなくても農地の引き渡しがあったときは、これをもってその後にその農地について所有権を取得した第三者に対応することができる。」

    {input_text}

    問題1：{{用語}}に関する次の記述のうち、正しいものを選択肢から選んでください。
    ・1：
    ・2：
    ・3：
    ・4：
    正解の選択肢番号：{{正解番号}}
    正解の理由：{{正解理由}}
    その他の選択肢が間違いである理由：{{間違い理由}}
    ...
    """
    
    # promptをロガーに出力する
    logging.info(f"Generated prompt: {prompt}")

    # OpenAI GPT-3にプロンプトを送信
    response = openai.ChatCompletion.create(
        # model="gpt-3.5-turbo-16k",  # 使用するGPT-3エンジン
        # model="gpt-3.5-turbo",  # 使用するGPT-3エンジン
        model="gpt-4",
        messages=[{"role": "user", "content": prompt}],  # 上記で作成したプロンプト
        api_key=api_key,  # APIキー
        # その他のパラメータ
    )

    # 応答から問題を解析
    questions = parse_questions_from_response(response)

    if not questions:
        logging.error("OpenAI API returned unexpected response format")
        raise HTTPException(status_code=500, detail="Failed to generate quizzes from OpenAI API")

    return questions


def parse_questions_from_response(response):
    questions = []
    output_text = response.choices[0]["message"]["content"].strip()

    # 問題ごとに分割
    problems = output_text.split("問題")[1:]

    for problem in problems:
        question = {}
        lines = problem.strip().split('\n')
        # 空白の要素を削除
        lines = [line for line in lines if line != '']
        logging.info(f"Generated lines: {lines}")

        # 質問文を抽出
        question['question_text'] = lines[0]

        # 選択肢を抽出
        question['options'] = [line.split("：")[1].strip() for line in lines[1:5]]

        # 正解の選択肢番号を抽出
        question['correct_choice'] = int(lines[5].split("：")[1].strip())

        # 正解の理由を抽出
        question['correct_reason'] = lines[6].split("：")[1].strip()

        # 間違いの理由を抽出
        question['wrong_reason'] = lines[7].split("：")[1].strip()

        questions.append(question)

    return questions


@app.post("/api/token", response_model=Token)
async def login_for_access_token(response: Response, user_login: UserLogin, db: Session = Depends(get_db)):
    user = get_user(db, user_login.username)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect username or password")
    
    if not verify_password(user_login.password, user.password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect username or password")

    access_token = create_access_token(data={"sub": user.username})
    response.set_cookie(
        key="access_token",
        value=f"Bearer {access_token}",
        httponly=True,  # JavaScriptからのアクセスを防ぐ
        max_age=3600,   # 例: 30分間の有効期限
        samesite="None",  # CSRF対策
        # domain="localhost",  # デプロイ時にはドメインを変更する
    )
    return {"access_token": access_token, "token_type": "bearer"}

# @app.post("/submit-quiz-answer/")
# async def submit_quiz_answer(answer: QuizAnswer, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
#     # ユーザーの選択をデータベースに保存
#     quiz = db.query(Quiz).filter(Quiz.id == answer.quiz_id).first()
#     if not quiz:
#         raise HTTPException(status_code=404, detail="Quiz not found")
#     quiz.user_answer = answer.user_choice
#     db.commit()

#     return {"detail": "Answer submitted successfully"}


@app.get("/api/histories", response_model=List[QuizCreate])
async def get_my_quizzes(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    # クイズ履歴をデータベースから取得するロジック
    quizzes = db.query(Quiz).filter(Quiz.user_id == current_user.id).all()
    return quizzes


@app.get("/api/logout")
async def logout(response: Response):
    response.delete_cookie(key="access_token")
    return {"message": "Logout Successful"}
