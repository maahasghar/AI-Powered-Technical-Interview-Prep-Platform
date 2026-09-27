import { Link } from "react-router-dom";
import { useAuth } from "../auth";
import { Difficulty, Status } from "../ui";
import "./Landing.css";

const features = [
  ["library", "Find your next challenge", "Browse coding problems by difficulty and category, with descriptions and public examples to get you started."],
  ["code", "Write Python in your browser", "Work through a problem alongside your code. Submit your solution directly from the editor."],
  ["check", "Understand your results", "See your verdict, test counts, and available runtime and memory measurements after evaluation."],
  ["spark", "Get structured coaching", "Review strengths and likely issues, ask for a hint, or request a suggested solution when you need one."],
  ["history", "Keep every attempt", "Revisit submitted code and results in your history. Pick up where your last attempt left off."],
  ["chart", "See your progress", "Track attempted and solved problems, with breakdowns by difficulty and category."],
];
const steps = [
  ["Choose a problem", "Find a topic and difficulty you want to work on."],
  ["Write your solution", "Read the examples and implement your approach in Python."],
  ["Submit for evaluation", "Your code runs against tests, and results update automatically."],
  ["Review and improve", "Explore feedback, revisit your approach, and try again."],
];

function FeatureIcon({ name }) {
  const paths = {
    library: <><rect x="4" y="4" width="16" height="16" rx="2" /><path d="M9 4v16M13 9h3M13 13h3" /></>,
    code: <><path d="m8 7-5 5 5 5m8-10 5 5-5 5m-3-13-2 16" /></>,
    check: <><circle cx="12" cy="12" r="9" /><path d="m8 12 3 3 5-6" /></>,
    spark: <><path d="m12 3 2.5 6.5L21 12l-6.5 2.5L12 21l-2.5-6.5L3 12l6.5-2.5Z" /></>,
    history: <><path d="M4 9a8 8 0 1 1 0 6M3 4v6h6m3-4v6l4 2" /></>,
    chart: <><path d="M4 3v18h17M8 16v-4m5 4V8m5 8V5" /></>,
  };
  return <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">{paths[name]}</svg>;
}

function PracticeLink({ children = "Start Practicing" }) {
  const { user } = useAuth();
  return <Link className="button primary landing-primary" to={user ? "/problems" : "/register"}>{children}<span aria-hidden="true">↗</span></Link>;
}

// A static illustration of the existing workspace, not a live submission.
function ProductPreview() {
  return <figure className="landing-preview">
    <figcaption><span><span className="landing-dot" /> Inside Interview Prep</span><span>Illustrative example</span></figcaption>
    <div className="landing-preview-grid">
      <div className="landing-preview-problem">
        <p className="eyebrow">Problem brief · Arrays</p>
        <div className="landing-preview-title"><h3>Pair Sum</h3><Difficulty value={1} /></div>
        <p>Find two indices whose values add up to the target.</p>
        <h4>Sample input</h4>
        <pre><code>{"nums = [2, 7, 11, 15]\ntarget = 9"}</code></pre>
        <h4>Expected output</h4>
        <code>[0, 1]</code>
        <div className="landing-preview-result"><Status value="PASSED" /><span>Example submission result</span></div>
      </div>
      <div className="landing-preview-editor">
        <div className="editor-heading"><strong>Your solution</strong><span>Python 3.11</span></div>
        <pre className="code-block"><code><span className="landing-code-comment"># Keep track of values already seen</span>{"\n"}<span className="landing-code-keyword">def</span>{" solve(nums, target):\n    seen = {}\n    for i, value in enumerate(nums):\n        complement = target - value\n        if complement in seen:\n            return [seen[complement], i]\n        seen[value] = i\n    return []"}</code></pre>
        <div className="landing-preview-coaching"><span className="landing-icon"><FeatureIcon name="spark" /></span><div><h4>AI coaching · Example</h4><p><strong>Strength:</strong> A lookup avoids scanning the array again for each number.</p><p><strong>Next step:</strong> Consider how repeated values affect your approach.</p></div></div>
      </div>
    </div>
  </figure>;
}

export default function Landing() {
  const { user } = useAuth();
  return <div className="landing">
    <section className="landing-hero" aria-labelledby="landing-title">
      <div>
        <p className="eyebrow">A workspace for your next interview</p>
        <h1 id="landing-title">Practice technical interviews with <span>AI-powered feedback.</span></h1>
        <p className="landing-lead">Turn each coding attempt into a chance to improve. Solve Python problems, submit your code for testing, and review structured feedback as you build your practice record.</p>
        <div className="landing-actions"><PracticeLink /><Link className="landing-secondary" to={user ? "/progress" : "/login"}>{user ? "View your progress" : "Sign In"}<span aria-hidden="true"> →</span></Link></div>
        <p className="landing-hero-note">Your code. Clear results. A next step.</p>
      </div>
      <aside className="landing-practice-note" aria-label="The practice cycle">
        <div className="landing-note-top"><span className="brand-icon" aria-hidden="true">&gt;_</span><span>A little practice,<br />a clearer approach.</span></div>
        <ol>{["Think it through", "Put it into code", "Learn from the result"].map((text, i) => <li key={text}><span>0{i + 1}</span>{text}</li>)}</ol>
        <a href="#product-preview">Take a look inside <span aria-hidden="true">↓</span></a>
      </aside>
    </section>

    <section className="landing-section landing-workflow" aria-labelledby="workflow-title">
      <div className="landing-section-heading"><p className="eyebrow">How it works</p><h2 id="workflow-title">One problem. A better understanding.</h2></div>
      <ol className="landing-steps">{steps.map(([title, detail], i) => <li key={title}><span className="landing-step-number">0{i + 1}</span><h3>{title}</h3><p>{detail}</p></li>)}</ol>
    </section>

    <section id="product-preview" className="landing-section" aria-labelledby="preview-title">
      <div className="landing-section-heading"><p className="eyebrow">From idea to insight</p><h2 id="preview-title">A place to work through it.</h2><p>Keep the problem in view, focus on your code, then use your results to decide what to try next.</p></div>
      <ProductPreview />
      <p className="landing-preview-caption">Workspace and feedback shown as an example. Your results and coaching depend on your submission.</p>
    </section>

    <section className="landing-section" aria-labelledby="features-title">
      <div className="landing-section-heading"><p className="eyebrow">Made for steady progress</p><h2 id="features-title">Everything your practice needs.</h2></div>
      <div className="landing-features">{features.map(([icon, title, detail]) => <article key={title}><span className="landing-icon"><FeatureIcon name={icon} /></span><h3>{title}</h3><p>{detail}</p></article>)}</div>
    </section>

    <section className="landing-engineering" aria-labelledby="engineering-title">
      <div><p className="eyebrow">Built for real practice</p><h2 id="engineering-title">Clear results.<br />Thoughtful guidance.</h2></div>
      <div><p>Your submission is evaluated against tests in an isolated execution environment. Results update as processing finishes, and your attempts stay in your history.</p><p>Test results determine correctness. AI coaching offers suggestions to help you reflect, explore another approach, and keep learning.</p></div>
    </section>

    <section className="landing-final" aria-labelledby="final-title"><p className="eyebrow">Small steps. Stronger solutions.</p><h2 id="final-title">Ready to start practicing?</h2><p>Choose a problem and give your next idea a try.</p><PracticeLink /></section>
  </div>;
}
