"use client";
import React, { useState, useEffect } from "react";

export default function QuizHistory() {
  const [quizzes, setQuizzes] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function fetchQuizHistory() {
      const response = await fetch("/api/histories", {
        credentials: "include",
      });
      const data = await response.json();
      setQuizzes(data);
      setLoading(false);
    }

    fetchQuizHistory();
  }, []);

  if (loading) return <div>Loading...</div>;

  return (
    <div className="flex flex-col items-center min-h-screen bg-white max-w-4xl mx-auto">
      <h1 className="text-2xl text-center mb-4">My Quiz History</h1>
      {quizzes.map((quiz, index) => (
        <div
          key={index}
          className="bg-gray-100 p-6 m-4 rounded bg-cyan-100 shadow-lg w-full"
        >
          {/* Here you can display the quiz data in your desired format */}
          <p>{quiz.question_text}</p>
          {/* Add more fields as needed */}
        </div>
      ))}
    </div>
  );
}
