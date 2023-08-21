export default async function handler(req, res) {
  const apiKey = req.body.apiKey;
  const category = req.body.category;

  // OpenAI APIを呼び出してクイズを生成するロジック
  // ...

  res.status(200).json({ question, options, answer });
}
