"use client";

import { useState } from "react";
import Link from "next/link";

// ... コンポーネントの他の部分

export default function Home() {
  const [quizzes, setQuizzes] = useState([]);
  const [currentQuiz, setCurrentQuiz] = useState(null);
  const [selectedNumberOfQuestions, setSelectedNumberOfQuestions] = useState(3);
  const [isLoading, setIsLoading] = useState(false);
  const [userAnswer, setUserAnswer] = useState({});
  const [showExplanation, setShowExplanation] = useState([]);
  const [apiKey, setApiKey] = useState("");

  const handleGenerateQuiz = async () => {
    setIsLoading(true); // API呼び出し前にローディング状態を設定
    const userapiKey = sessionStorage.getItem("apiKey");
    const fetchPromise = await fetch("/api/generate-quiz", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      credentials: "include",
      body: JSON.stringify({
        number_of_questions: selectedNumberOfQuestions, // この行を追加
        api_key: apiKey,
      }),
    });

    const timeoutPromise = new Promise((_, reject) =>
      setTimeout(() => reject(new Error("Request timed out")), 60000)
    );

    try {
      const response = await Promise.race([fetchPromise, timeoutPromise]);

      if (response.status === 401) {
        alert("セッションがタイムアウトしました。再ログインしてください。");
        document.cookie =
          "access_token=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/;";
        window.location.href = "/"; // ログインページへリダイレクト
        setIsLoading(false);
        return;
      }
      if (response.status === 422) {
        const errorDetail = await response.json();
        console.error("Error detail:", errorDetail);
        return; // または適切なエラー処理
      }

      if (!response.ok) {
        console.error("An error occurred:", response.statusText);
        return; // または適切なエラー処理
      }

      const { quizzes } = await response.json();
      setIsLoading(false); // API呼び出し後にローディング状態を解除
      setQuizzes(quizzes);
      setCurrentQuiz(quizzes[0]); // 最初のクイズを表示

      setUserAnswer({}); // 選択した回答をリセット
      setShowExplanation([]); // 解説の表示状態をリセット
    } catch (error) {
      if (error.message === "Request timed out") {
        console.error("The request timed out.");
      } else {
        console.error("An unknown error occurred:", error);
      }
    } finally {
      setIsLoading(false); // API呼び出し後にローディング状態を解除
    }
  };

  const handleNumberOfQuestionsChange = (event) => {
    setSelectedNumberOfQuestions(event.target.value);
  };

  const handleAnswerSelection = (selectedOption, quizIndex) => {
    let newUserAnswer = { ...userAnswer };
    newUserAnswer[quizIndex] = selectedOption;
    setUserAnswer(newUserAnswer);
    toggleExplanation(quizIndex);
  };

  const toggleExplanation = (quizIndex) => {
    const newShowExplanation = [...showExplanation];
    newShowExplanation[quizIndex] = !newShowExplanation[quizIndex];
    setShowExplanation(newShowExplanation);
  };

  return (
    <div className="flex flex-col items-center min-h-screen bg-white max-w-4xl mx-auto">
      {/* <div className="w-full p-4 bg-gray-100 flex justify-center">
        <Link href="/quiz_history" className="text-blue-500 hover:underline">
          My Quiz History
        </Link>
      </div> */}
      <h1 className="text-2xl text-center mb-4">宅建練習問題ジェネレータ</h1>
      <img
        src="/images/house_ie_sagashi.png"
        alt="Description of Image"
        className="w-64 h-64 mx-auto mb-4"
      />
      <div className="mb-6">
        {" "}
        {/* APIキー入力フィールドの追加 */}
        <label
          className="block text-gray-700 text-sm font-bold mb-2"
          htmlFor="apiKey"
        >
          OpenAI API Key
        </label>
        <label className="block text-gray-400 text-xs font-bold mb-2">
          入力されたAPIキーは当サイトに保存されず、一時的に問題生成にのみ使用されます。
        </label>
        <input
          className="shadow appearance-none border rounded w-full py-2 px-3 text-gray-700 leading-tight focus:outline-none focus:shadow-outline"
          id="apiKey"
          type="text"
          placeholder="Your OpenAI API Key"
          value={apiKey}
          onChange={(e) => setApiKey(e.target.value)}
        />
      </div>
      <div className="flex items-center mb-4">
        <label className="mr-4">生成する問題数を選択: </label>
        <select
          onChange={handleNumberOfQuestionsChange}
          value={selectedNumberOfQuestions}
          className="border p-2 rounded"
        >
          <option value={1}>1</option>
          <option value={2}>2</option>
          <option value={3}>3</option>
          <option value={4}>4</option>
          <option value={5}>5</option>
        </select>
      </div>
      <button
        onClick={handleGenerateQuiz}
        className="bg-blue-500 hover:bg-blue-700 text-white font-bold py-2 px-4 rounded mt-4"
        disabled={isLoading}
      >
        {isLoading ? "Loading..." : "Generate Quiz"}
      </button>
      {quizzes.map((quiz, quizIndex) => (
        <div
          key={quizIndex}
          className="bg-gray-100 p-6 m-4 rounded bg-cyan-100 shadow-lg w-full"
        >
          <h2 className="text-xl mb-4">問題{quiz.question_text}</h2>
          {quiz.options && Array.isArray(quiz.options) ? (
            quiz.options.map((option, optionIndex) => (
              <div key={optionIndex} className="mb-2">
                <button
                  onClick={() => handleAnswerSelection(optionIndex, quizIndex)}
                  className={`border rounded p-2 hover:bg-gray-200 transition text-left w-full 
                ${
                  userAnswer[quizIndex] !== undefined
                    ? optionIndex === quiz.correct_choice - 1
                      ? "bg-green-100"
                      : optionIndex === userAnswer[quizIndex]
                      ? "bg-red-100"
                      : "bg-white"
                    : ""
                }`}
                  disabled={userAnswer[quizIndex] !== undefined}
                >
                  選択肢{optionIndex + 1}: {option}
                </button>
              </div>
            ))
          ) : (
            <p>No options available.</p>
          )}
          {userAnswer && quizIndex in userAnswer ? (
            <div className="mt-4">
              {userAnswer[quizIndex] === quiz.correct_choice - 1 ? (
                <p className="text-lg">正解！！</p>
              ) : (
                <p className="text-lg">残念！！</p>
              )}

              {showExplanation[quizIndex] && (
                <div>
                  <p>正解選択肢: {quiz.correct_choice}</p>
                  <p>解説: {quiz.correct_reason}</p>
                  <p>誤選択肢の理由: {quiz.wrong_reason}</p>
                </div>
              )}
            </div>
          ) : null}
        </div>
      ))}
    </div>
  );
}
