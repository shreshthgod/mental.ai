import { useEffect } from "react";
import { Link, useLocation } from "react-router-dom";
import { Reveal } from "../components/motion/Reveal";
import { Footer } from "../components/chrome/Footer";

const METHOD_STAGES = [
  { n: "01", name: "Data sourcing", d: "Three public datasets: Combined Data.csv (53,043 rows), Suicide_Detection.csv (232,074 rows), Emotion_Sentiment_DataSet.csv (160,000 rows - lexicon features only)." },
  { n: "02", name: "Raw EDA", d: "Cross-dataset overlap analysis (51.6% of Combined Data unique text overlaps the emotion corpus), language and quality profiling." },
  { n: "03", name: "Unified datasets", d: "Primary (7-class) and urgency (binary) datasets built with stratified 80/10/10 splits, random_state=42." },
  { n: "04", name: "Cleaning", d: "Encoding normalization (ftfy), deduplication, garbage-row filtering - 53,043 → 51,048 and 232,074 → 231,943 rows." },
  { n: "05", name: "Preprocessing", d: "Tokenization + lemmatization with defensive failure handling; UTF-8 crash (U+0130) found and fixed during hardening." },
  { n: "06", name: "Cleaned EDA", d: "Post-clean distributions, urgency keyword candidates, non-English sampling." },
  { n: "07", name: "Feature extraction", d: "38 handcrafted features (VADER, NRC emotion lexicon, readability, pronoun/absolutist ratios, urgency keywords) + TF-IDF unigram/bigram (min_df=5, max_df=0.9, 30,000 terms)." },
  { n: "08", name: "Class imbalance", d: "13.6:1 ratio on the primary track (Normal 30.8% → Personality disorder 2.3%) - handled with class weights, no resampling." },
  { n: "09", name: "Model training", d: "Primary: XGBoost over 38 handcrafted + chi²-selected 1,500 TF-IDF terms (1,538 dims). Urgency: logistic regression over the full 30,000-term space." },
  { n: "10", name: "Evaluation", d: "Held-out test evaluation + threshold sweep. Urgency deployed at 0.15: recall 0.934 → 0.987, precision 0.952 → 0.840." },
  { n: "11", name: "Explainability & errors", d: "Global SHAP importance for both models; misclassification and confusion-pair analysis; false-negative review at the deployed threshold." },
  { n: "12", name: "Packaging", d: "Frozen artifacts (models, vectorizers, chi² selector, lexicons, config) behind the MentalHealthScreener inference API." },
];

function Section({ id, num, title, children }: { id?: string; num: string; title: string; children: React.ReactNode }) {
  return (
    <section id={id} className="rsection">
      <Reveal>
        <div className="rsection__head">
          <span className="rsection__num">{num}</span>
          <h2 className="rsection__title">{title}</h2>
        </div>
      </Reveal>
      <div className="rsection__body">{children}</div>
    </section>
  );
}

export function Research() {
  const location = useLocation();
  useEffect(() => {
    if (location.hash) {
      const t = setTimeout(() => {
        document.getElementById(location.hash.slice(1))?.scrollIntoView({ behavior: "smooth" });
      }, 300);
      return () => clearTimeout(t);
    }
  }, [location]);

  return (
    <>
      <main id="main" className="research">
        <div className="research__inner">
          <div className="research__hero">
            <Reveal>
              <p className="label label--accent">Research documentation</p>
            </Reveal>
            <Reveal delayMs={80}>
              <h1 className="research__title">RESEARCH</h1>
            </Reveal>
            <Reveal delayMs={160}>
              <p className="research__lede">
                A text-based mental-health screening pipeline with two independent
                prediction tracks, trained on public proxy-label datasets. Every
                figure on this page is taken from the repository - the model card,
                the evaluation outputs and the packaged config - and the gaps are
                stated alongside the results.
              </p>
            </Reveal>
          </div>

          <Section num="01" title="Problem">
            <Reveal>
              <p>
                Online language carries mental-health signals long before they reach
                a clinic. The research question: can a reproducible classical-NLP
                pipeline surface <strong>condition patterns</strong> and an
                <strong> independent urgency signal</strong> from raw text - honestly
                enough to route human review, without ever posing as a diagnosis?
              </p>
            </Reveal>
            <Reveal delayMs={80}>
              <p>
                The two tracks are deliberately independent. The condition
                classifier answers "what pattern does this language resemble?"; the
                urgency model answers "should a human look at this soon?". Merging
                them would conflate two different decisions.
              </p>
            </Reveal>
          </Section>

          <Section num="02" title="Data">
            <div className="rsection__cols">
              <Reveal className="rfact">
                <p className="rfact__k">Combined Data.csv</p>
                <p className="rfact__v"><span className="num">53,043</span> rows → <span className="num">51,048</span> after cleaning - primary 7-class dataset (Normal, Depression, Suicidal, Anxiety, Bipolar, Stress, Personality disorder)</p>
              </Reveal>
              <Reveal className="rfact" delayMs={80}>
                <p className="rfact__k">Suicide_Detection.csv</p>
                <p className="rfact__v"><span className="num">232,074</span> rows → <span className="num">231,943</span> after cleaning - binary urgency dataset</p>
              </Reveal>
              <Reveal className="rfact" delayMs={120}>
                <p className="rfact__k">Emotion_Sentiment_DataSet.csv</p>
                <p className="rfact__v"><span className="num">160,000</span> rows (87,983 unique) - emotion-lexicon feature engineering only, never training labels</p>
              </Reveal>
              <Reveal className="rfact" delayMs={160}>
                <p className="rfact__k">Labels</p>
                <p className="rfact__v">Proxy labels - subreddit of origin via Pushshift / Kaggle sources. Not clinician-verified diagnoses.</p>
              </Reveal>
            </div>
          </Section>

          <Section id="method" num="03" title="Pipeline">
            <Reveal>
              <p>Twelve orchestrated stages, from raw CSVs to a packaged inference service. Hover a stage for its role.</p>
            </Reveal>
            <div className="method">
              {METHOD_STAGES.map((s) => (
                <div key={s.n} className="method__row" tabIndex={0}>
                  <span className="method__num">{s.n}</span>
                  <span className="method__name">{s.name}</span>
                  <span className="method__desc">{s.d}</span>
                </div>
              ))}
            </div>
          </Section>

          <Section num="04" title="Feature engineering">
            <div className="rsection__cols">
              <Reveal className="rfact">
                <p className="rfact__k">Handcrafted - 38 dims</p>
                <p className="rfact__v">Surface statistics, VADER sentiment, NRC emotion lexicon, readability scores, pronoun & absolutist-language ratios, curated urgency keywords, emotion-lexicon matches.</p>
              </Reveal>
              <Reveal className="rfact" delayMs={80}>
                <p className="rfact__k">TF-IDF - 30,000 terms</p>
                <p className="rfact__v">Unigram + bigram, min_df=5, max_df=0.9. The primary track applies chi² selection to 1,500 terms; the urgency track keeps the full space.</p>
              </Reveal>
            </div>
          </Section>

          <Section num="05" title="Models">
            <div className="rsection__cols">
              <Reveal className="rfact">
                <p className="rfact__k">Primary - XGBoost</p>
                <p className="rfact__v">7-class gradient-boosted trees over 1,538 dimensions (38 handcrafted + 1,500 chi²-selected TF-IDF terms), trained with class weights.</p>
              </Reveal>
              <Reveal className="rfact" delayMs={80}>
                <p className="rfact__k">Urgency - Logistic regression</p>
                <p className="rfact__v">Binary safety net over the full 30,000-term TF-IDF space. Deployed threshold 0.15 (default 0.5) - chosen for recall, documented as a trade.</p>
              </Reveal>
            </div>
          </Section>

          <Section num="06" title="Evaluation">
            <div className="rmetric-row">
              <Reveal className="rmetric">
                <p className="rmetric__v num">0.6926</p>
                <p className="rmetric__l">Primary macro-F1</p>
                <p className="rmetric__n">7-class XGBoost, held-out test split</p>
              </Reveal>
              <Reveal className="rmetric" delayMs={80}>
                <p className="rmetric__v num">0.9431</p>
                <p className="rmetric__l">Urgency macro-F1 @ 0.5</p>
                <p className="rmetric__n">Default decision threshold</p>
              </Reveal>
              <Reveal className="rmetric" delayMs={160}>
                <p className="rmetric__v num">0.8981</p>
                <p className="rmetric__l">Urgency macro-F1 @ 0.15</p>
                <p className="rmetric__n">Deployed threshold - lower by design, in exchange for 0.987 suicide recall</p>
              </Reveal>
            </div>
            <Reveal delayMs={120}>
              <p>
                All figures are <strong>point estimates from a single experiment</strong>;
                no confidence intervals or statistical significance tests were
                performed - a documented gap, not an oversight we hide.
              </p>
            </Reveal>
          </Section>

          <Section num="07" title="Explainability">
            <Reveal>
              <p>
                <strong>Global</strong> SHAP analysis exists for both models
                (global importance rankings and bar plots, preserved in Step 11).
                This describes what the models rely on <strong>in aggregate</strong> -
                it is not a per-prediction explanation, and the interface never
                presents it as one. Misclassification CSVs and confusion-pair
                analysis are preserved for error review.
              </p>
            </Reveal>
          </Section>

          <Section id="limitations" num="08" title="Limitations">
            <div className="rsection__cols">
              <Reveal className="rfact"><p className="rfact__k">Not clinical</p><p className="rfact__v">Proxy labels, no clinician verification. Outputs are screening signals for human review - never diagnoses, treatment guidance, or autonomous crisis response.</p></Reveal>
              <Reveal className="rfact" delayMs={60}><p className="rfact__k">Overlap</p><p className="rfact__v">51.6% of Combined Data unique text overlaps the emotion corpus; no author-level split exists, so exact-text deduplication is the only leakage mitigation.</p></Reveal>
              <Reveal className="rfact" delayMs={120}><p className="rfact__k">Imbalance</p><p className="rfact__v">13.6:1 primary class ratio (Normal 30.8% → Personality disorder 2.3%); class weights applied, minority-class errors remain the dominant failure mode.</p></Reveal>
              <Reveal className="rfact" delayMs={180}><p className="rfact__k">Scope</p><p className="rfact__v">Text only, English-skewed. No speech module, no multilingual validation, no transformer in the packaged inference path.</p></Reveal>
            </div>
          </Section>

          <Section id="repro" num="09" title="Reproducibility">
            <Reveal>
              <p>The full pipeline, artifacts and service are reproducible from the repository:</p>
            </Reveal>
            <Reveal delayMs={80}>
              <div className="code-block">{`# dependencies + NLTK resources
pip install -r "Step 12 - Packaging/package/requirements.txt"

# run the API
python -m uvicorn api.api:app --host 0.0.0.0 --port 8000

# or as a container
docker build -t mental-health-screening .
docker run -p 8000:8000 mental-health-screening

# verification: 6 PASS · 2 FAIL · 1 SKIPPED (documented)
python scripts/verify_project.py`}</div>
            </Reveal>
            <Reveal delayMs={120}>
              <p className="research__note">
                Known gaps preserved in the repository: urgency TF-IDF matrices are
                partially regenerated (val/test pending a &gt;10-minute preprocessing
                run - inference is unaffected), no experiment-tracking ledger, and
                the two verification FAILs are path discrepancies, not runtime
                failures. See REPRODUCIBILITY.md and FINAL_DELIVERABLE.md.
              </p>
            </Reveal>
            <Reveal delayMs={160}>
              <div style={{ marginTop: 8 }}>
                <Link to="/screen" className="cta cta--primary">
                  Run the live model <span className="cta__arrow" aria-hidden="true">→</span>
                </Link>
              </div>
            </Reveal>
          </Section>
        </div>
      </main>
      <Footer />
    </>
  );
}
