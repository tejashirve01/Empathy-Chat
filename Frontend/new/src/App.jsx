import React, { useState, useEffect, useRef } from "react";
import { BrowserRouter as Router, Routes, Route, useNavigate } from "react-router-dom";
import "./App.css";

/* Dummy user list and credentials */
const validUsers = [
  { username: "tejas",  password: "tejas123",  name: "Tejas",  img: "https://via.placeholder.com/50/09f/fff.png" },
  { username: "sumedh", password: "sumedh123", name: "Sumedh", img: "https://via.placeholder.com/50/222/fff.png" },
  { username: "anuj",   password: "anuj123",   name: "Anuj",   img: "https://via.placeholder.com/50/444/fff.png" },
  { username: "yash",   password: "yash123",   name: "Yash",   img: "https://via.placeholder.com/50/666/fff.png" },
];

/* 1) LANDING PAGE */
function LandingPage() {
  const navigate = useNavigate();
  return (
    <div className="landing-container">
      <div className="landing-nav">
        <button onClick={() => navigate("/login")} className="landing-login-btn">
          Login
        </button>
      </div>
      <div className="landing-content">{/* optional hero text */}</div>
    </div>
  );
}

/* 2) LOGIN PAGE */
function LoginPage() {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const navigate = useNavigate();

  const handleLogin = () => {
    const user = validUsers.find(u => u.username === username && u.password === password);
    if (user) {
      localStorage.setItem("currentUser", JSON.stringify(user));
      navigate("/dashboard");
    } else {
      alert("Invalid credentials!");
    }
  };

  return (
    <div className="login-bg">
      <div className="login-container">
        <h2>Empathy Chat</h2>
        <input
          type="text"
          placeholder="Username"
          value={username}
          onChange={(e) => setUsername(e.target.value.trim().toLowerCase())}
        />
        <input
          type="password"
          placeholder="Password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
        />
        <button onClick={handleLogin}>Login</button>
      </div>
    </div>
  );
}

/* 3A) SIDEBAR */
function Sidebar({ contacts, selectedContact, onSelect }) {
  const [searchQuery, setSearchQuery] = useState("");
  const filteredContacts = contacts.filter((contact) =>
    contact.name.toLowerCase().includes(searchQuery.toLowerCase())
  );

  return (
    <div className="sidebar">
      <div className="sidebar-header">
        <div className="sidebar-icons">
          <span className="icon">☰</span>
          <span className="icon">🟢</span>
          <span className="icon">⚙️</span>
        </div>
        <h2 className="sidebar-title">Chats</h2>
      </div>
      <div className="sidebar-search">
        <input
          type="text"
          placeholder="Search or start a new chat"
          className="search-input"
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
        />
      </div>
      <div className="contacts-list">
        {filteredContacts.map((contact) => (
          <div
            key={contact.username}
            className={`contact-row ${
              selectedContact && selectedContact.username === contact.username
                ? "active"
                : ""
            }`}
            onClick={() => onSelect(contact)}
          >
            <img src={contact.img} alt={contact.name} className="contact-avatar" />
            <div className="contact-info">
              <div className="contact-name">{contact.name}</div>
              <div className="contact-lastmsg">{contact.lastMsg}</div>
            </div>
            <div className="contact-time">{contact.time}</div>
          </div>
        ))}
      </div>
    </div>
  );
}

/* 3B) CHAT AREA: placeholder or actual chat */
function ChatArea({ contact }) {
  if (!contact) {
    return (
      <div className="chat-area-placeholder">
        <h1>WhatsApp for Windows</h1>
        <p>
          Send and receive messages without keeping your phone online.
          <br />
          Use WhatsApp on up to 4 linked devices and 1 phone at the same time.
        </p>
      </div>
    );
  }
  return <FunctionalChat contact={contact} />;
}

/* 3C) FUNCTIONAL CHAT */
function FunctionalChat({ contact }) {
  const [messages, setMessages] = useState([]);
  const [inputValue, setInputValue] = useState("");
  const [professionalMode, setProfessionalMode] = useState(false);
  const socketRef = useRef(null);

  // Current user info
  const currentUser = JSON.parse(localStorage.getItem("currentUser"));

  useEffect(() => {
    // Open a WebSocket using the current user's username
    const ws = new WebSocket(`ws://localhost:8000/ws/${currentUser.username}`);
    socketRef.current = ws;

    // We do NOT show "Connected" or "Disconnected" messages
    ws.onmessage = (event) => {
      // The server sends something like "tejas:Hello"
      // We parse out the sender from the message
      const msg = event.data;
      const colonIndex = msg.indexOf(":");
      if (colonIndex === -1) {
        // Unexpected format
        return;
      }
      const sender = msg.slice(0, colonIndex);
      const text = msg.slice(colonIndex + 1);

      // If the sender is the same as me, ignore (no echo)
      // Otherwise, show it as "received" on the left
      if (sender !== currentUser.username) {
        setMessages((prev) => [...prev, { message: text, className: "received" }]);
      }
    };

    return () => {
      ws.close();
    };
  }, [contact, currentUser.username]);

  const sendMessage = () => {
    if (!socketRef.current || !inputValue.trim()) return;

    // Local echo => add your message on the right
    setMessages((prev) => [...prev, { message: inputValue, className: "personal" }]);

    // Send to server (only the recipient will receive it)
    const mode = professionalMode ? "professional" : "filter";
    const data = JSON.stringify({
      text: inputValue,
      mode,
      to: contact.username,
    });
    socketRef.current.send(data);

    setInputValue("");
  };

  const handleKeyPress = (e) => {
    if (e.key === "Enter") {
      sendMessage();
    }
  };

  return (
    <div className="chat-area">
      <div className="chat-header">
        <h1>{contact.name}</h1>
      </div>
      <div className="chat-body">
        {messages.map((msgObj, i) => (
          <div key={i} className={`message ${msgObj.className}`}>
            {msgObj.message}
          </div>
        ))}
      </div>
      <div className="chat-footer">
        <label className="toggle-switch">
          <input
            type="checkbox"
            checked={professionalMode}
            onChange={() => setProfessionalMode(!professionalMode)}
          />
          <span className="slider"></span>
        </label>
        <span className="toggle-label">Professional Mode</span>

        <div className="chat-input">
          <input
            type="text"
            placeholder="Type a message..."
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            onKeyPress={handleKeyPress}
          />
          {/* Arrow icon instead of 'Send' */}
          <button onClick={sendMessage} className="send-arrow-btn">
            ➤
          </button>
        </div>
      </div>
    </div>
  );
}

/* 3D) DASHBOARD */
function Dashboard() {
  const currentUser = JSON.parse(localStorage.getItem("currentUser"));

  // Show all other users as contacts
  const contacts = validUsers
    .filter((u) => u.username !== currentUser.username)
    .map((u) => ({
      username: u.username,
      name: u.name,
      lastMsg: `Hi, I'm ${u.name}`,
      time: "Now",
      img: u.img,
    }));

  // By default, no contact selected => empty chat
  const [selectedContact, setSelectedContact] = useState(null);

  return (
    <div className="dashboard">
      <Sidebar
        contacts={contacts}
        selectedContact={selectedContact}
        onSelect={setSelectedContact}
      />
      <div className="main-area">
        <ChatArea contact={selectedContact} />
      </div>
    </div>
  );
}

/* MAIN APP */
export default function App() {
  return (
    <Router>
      <Routes>
        <Route path="/" element={<LandingPage />} />
        <Route path="/login" element={<LoginPage />} />
        <Route path="/dashboard" element={<Dashboard />} />
      </Routes>
    </Router>
  );
}
