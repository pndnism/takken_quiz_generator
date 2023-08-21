"use client";

import React, { useState } from "react";

export default function Login() {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");

  const handleRegister = async () => {
    const response = await fetch("/api/register", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        username: username,
        password: password,
      }),
    });

    if (response.ok) {
      // 登録成功時の処理、例えばログインページにリダイレクトするなど
      console.log("Registration successful");
    } else {
      // エラーハンドリングを行います
      console.error("Registration failed");
    }
  };

  const handleLogin = async () => {
    // ここでAPIを呼び出してユーザー認証を行います
    console.log("NODE_ENV:", process.env.NODE_ENV);

    const response = await fetch("/api/token", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      credentials: "include",
      body: JSON.stringify({
        username: username, // useStateで管理されているusernameの状態
        password: password, // useStateで管理されているpasswordの状態
      }),
    });

    if (response.ok) {
      window.location.href = "/generator/"; // or use your routing library's redirect method
    } else {
      // エラーハンドリングを行います
      console.error("Login failed");
    }
  };

  return (
    <div className="mt-8 flex flex-col items-center max-w-4xl mx-auto">
      <h2 className="text-2xl mb-4">ログイン・新規登録</h2>
      <div className="mb-4">
        <label
          className="block text-gray-700 text-sm font-bold mb-2"
          htmlFor="username"
        >
          Username
        </label>
        <input
          className="shadow appearance-none border rounded w-full py-2 px-3 text-gray-700 leading-tight focus:outline-none focus:shadow-outline"
          id="username"
          type="text"
          placeholder="Username"
          value={username}
          onChange={(e) => setUsername(e.target.value)}
        />
      </div>
      <div className="mb-6">
        <label
          className="block text-gray-700 text-sm font-bold mb-2"
          htmlFor="password"
        >
          Password
        </label>
        <input
          className="shadow appearance-none border rounded w-full py-2 px-3 text-gray-700 mb-3 leading-tight focus:outline-none focus:shadow-outline"
          id="password"
          type="password"
          placeholder="Password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
        />
      </div>
      <div className="flex items-center justify-between">
        <button
          className="bg-green-500 hover:bg-green-700 text-white font-bold py-2 px-4 rounded focus:outline-none focus:shadow-outline mr-4"
          type="button"
          onClick={handleLogin}
        >
          Login
        </button>
        <button
          className="bg-blue-500 hover:bg-blue-700 text-white font-bold py-2 px-4 rounded focus:outline-none focus:shadow-outline"
          type="button"
          onClick={handleRegister}
        >
          Register
        </button>
      </div>
    </div>
  );
}
