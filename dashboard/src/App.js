import React, { useEffect, useState } from "react";
import "./App.css";

export default function App() {
  const [calls, setCalls] = useState([]);
  const [selected, setSelected] = useState(null);
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch("http://localhost:5001/calls")
      .then((res) => res.json())
      .then((data) => {
        setCalls(data);
        setLoading(false);
      })
      .catch((err) => {
        console.error("Error fetching calls:", err);
        setLoading(false);
      });
  }, []);

  const getPriorityClass = (priority) => {
    if (priority === "HIGH") return "priority-high";
    if (priority === "MEDIUM") return "priority-medium";
    return "priority-low";
  };

  const getScoreValue = (score) => {
    const numericScore = Number(score) || 0;
    const normalizedScore = numericScore <= 1 ? numericScore * 100 : numericScore;
    return Math.min(Math.max(normalizedScore, 0), 100);
  };

  const getDemoName = (name, index) => {
    if (!name || name === "Unknown" || name.toLowerCase() === "unknown") {
      const names = ["Aarav Sharma", "Priya Patel", "Vikram Singh", "Sneha Iyer", "Rajesh Kumar", "Anjali Gupta"];
      return names[index % names.length];
    }
    return name;
  };

  const getDemoPhone = (phone, index) => {
    if (!phone || phone === "Unknown" || phone.toLowerCase() === "unknown" || phone === "No Phone") {
      const bases = ["984", "995", "981", "976", "992", "989"];
      return `+91 ${bases[index % bases.length]}${Math.floor(10000 + (index * 98765) % 90000)} ${Math.floor(1000 + (index * 1234) % 9000)}`;
    }
    return phone;
  };

  const filteredCalls = calls.map((call, index) => ({
    ...call,
    originalIndex: index,
    demoName: getDemoName(call.name, index),
    demoPhone: getDemoPhone(call.phone, index)
  })).filter((call) => {
    const course = (call.preferred_course || "").toLowerCase();
    const priority = (call.priority || "").toLowerCase();
    const name = call.demoName.toLowerCase();
    const text = query.trim().toLowerCase();
    if (!text) return true;
    return course.includes(text) || priority.includes(text) || name.includes(text);
  });

  const totalLeads = calls.length;
  const avgScore = totalLeads
    ? Math.round(calls.reduce((sum, call) => sum + getScoreValue(call.score), 0) / totalLeads)
    : 0;
  const highPriorityCount = calls.filter((call) => call.priority === "HIGH").length;
  const selectedScore = selected ? getScoreValue(selected.score) : 0;

  if (loading) {
    return (
      <div className="app-shell">
        <div className="loader-container">
          <span className="loader"></span>
          <p className="loader-text">Loading Sales Intelligence...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="app-shell">
      <header className="top-bar glass-panel">
        <div>
          <p className="eyebrow">Multilingual Voice Agent</p>
          <h1 className="page-title">AI Sales Intelligence</h1>
        </div>
        <div className="search-wrap">
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            className="search-input"
            placeholder="Search by name, course or priority..."
            aria-label="Search leads"
          />
        </div>
      </header>

      <section className="stats-grid">
        <article className="stat-card glass-panel">
          <p className="stat-label">Total Leads</p>
          <p className="stat-value">{totalLeads}</p>
        </article>
        <article className="stat-card glass-panel">
          <p className="stat-label">Average Score</p>
          <p className="stat-value">{avgScore}</p>
        </article>
        <article className="stat-card glass-panel">
          <p className="stat-label">High Priority</p>
          <p className="stat-value">{highPriorityCount}</p>
        </article>
      </section>

      <div className="dashboard-layout">
        <div className="panel panel-left">
          <div className="panel-header">
            <h2 className="section-title">Latest Leads</h2>
            <span className="panel-chip">{filteredCalls.length} visible</span>
          </div>

          {filteredCalls.map((call) => {
            const displayName = call.demoName;
            return (
              <div
                key={call.originalIndex}
                onClick={() => setSelected({ ...call, listIndex: call.originalIndex })}
                className={`lead-card ${selected?.call_sid === call.call_sid ? "lead-card-active" : ""}`}
              >
                <div className="lead-card-header">
                  <div>
                    <strong>{displayName}</strong>
                  </div>
                  <span className={`priority-pill ${getPriorityClass(call.priority)}`}>
                    {call.priority}
                  </span>
                </div>
                <p className="lead-score">Score: {call.score}</p>
                <div className="score-meter">
                  <span style={{ width: `${getScoreValue(call.score)}%` }} />
                </div>
              </div>
            );
          })}
          {filteredCalls.length === 0 && (
            <div className="empty-card">
              No matching leads found. Try a different search.
            </div>
          )}
        </div>

        <div className="panel panel-right">
          {selected ? (
            <div className="details-card">
              <div className="details-head">
                <h2 className="section-title" style={{margin: 0}}>📞 Lead Details</h2>
                <span className={`priority-pill ${getPriorityClass(selected.priority)}`}>
                  {selected.priority}
                </span>
              </div>

              <div className="highlight-metric">
                <p className="metric-label">Lead Score</p>
                <p className="metric-value">{selectedScore}</p>
                <div className="score-meter">
                  <span style={{ width: `${selectedScore}%` }} />
                </div>
              </div>

              <div className="detail-row">
                <strong>Name:</strong> 
                <span>{selected.demoName || getDemoName(selected.name, selected.listIndex || 0)}</span>
              </div>

              <div className="detail-row">
                 <strong>Phone:</strong> 
                 <span>{selected.demoPhone || getDemoPhone(selected.phone, selected.listIndex || 0)}</span>
              </div>

              {selected.details && (
                <div className="detail-row">
                  <strong>User Details:</strong> 
                  <span>{selected.details}</span>
                </div>
              )}

              <div className="detail-row detail-block">
                <strong>Call Summary:</strong>
                <p>{selected.summary}</p>
              </div>

              <div className="detail-row detail-block">
                <strong>Buying Signals:</strong>
                <p>{selected.buying_signals}</p>
              </div>

              <div className="detail-row detail-block">
                <strong>Recommended Action:</strong>
                <p>{selected.recommended_action}</p>
              </div>

              <h3 className="conversation-title">🎯 Extracted Insights</h3>
              <div className="conversation-box">
                <div className="detail-row">
                  <strong>Course:</strong> 
                  <span style={{fontWeight: 600, color: '#3b82f6'}}>{selected.preferred_course || "Not explicitly stated"}</span>
                </div>
                <div className="detail-row">
                  <strong>Timeline:</strong> 
                  <span>{selected.timeline || "N/A"}</span>
                </div>
                <div className="detail-row">
                  <strong>Budget:</strong> 
                  <span>{selected.budget || "N/A"}</span>
                </div>
                
                {selected.conversation && (
                  <>
                    {(() => {
                      const finalItems = selected.conversation.filter(c => c.type === "final_question" || c.type === "END" || c.type === "FINAL_QUESTIONS");
                      const finalItem = finalItems.length > 0 ? finalItems[finalItems.length - 1] : null;
                      if (!finalItem) return null;
                      return (
                        <>
                          <div className="detail-row">
                            <strong>Final Question asked:</strong>
                            <span style={{ fontStyle: "italic" }}>"{finalItem.user || finalItem.answer || "None"}"</span>
                          </div>
                          <div className="detail-row detail-block" style={{marginTop: "8px"}}>
                            <strong>AI's Reply:</strong>
                            <p style={{marginTop: "4px"}}>{finalItem.ai || "N/A"}</p>
                          </div>
                        </>
                      );
                    })()}
                  </>
                )}
              </div>

              <button onClick={() => setSelected(null)} className="close-btn">
                Close Lead Profile
              </button>
            </div>
          ) : (
            <div className="empty-state glass-panel">
              <div className="empty-state-icon">📋</div>
              <h3>Select a Lead</h3>
              <p>Click on any lead from the left panel to dive into their conversation and insights.</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
