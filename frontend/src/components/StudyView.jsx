import { useState } from "react";
import LearnView from "./LearnView.jsx";
import ReviewView from "./ReviewView.jsx";

// Two clearly separated zones, switched by a segmented control:
//   學新字 = first-time learning (no flip / no self-grade)
//   複習   = SM-2 due reviews (flip + self-grade, shuffled)
export default function StudyView({ onAuthLost }) {
  const [mode, setMode] = useState("review");
  return (
    <div className="studyview">
      <div className="segmented">
        <button className={mode === "learn" ? "on" : ""} onClick={() => setMode("learn")}>學新字</button>
        <button className={mode === "review" ? "on" : ""} onClick={() => setMode("review")}>複習</button>
      </div>
      {mode === "learn"
        ? <LearnView onAuthLost={onAuthLost} />
        : <ReviewView onAuthLost={onAuthLost} />}
    </div>
  );
}
