import { useState } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import { sendFeedback } from '../api/client'
import SkinRecommendation from '../components/SkinRecommendation'
import styles from './ResultsPage.module.css'

function formatReply(text) {
  if (!text) return ''
  return text.split(/(\*\*[^*]+\*\*)/g).map((part, i) => {
    if (part.startsWith('**') && part.endsWith('**'))
      return <strong key={i}>{part.slice(2, -2)}</strong>
    return <span key={i}>{part}</span>
  })
}

function StepDetail({ label, value }) {
  if (!value) return null
  return (
    <div className={styles.detailRow}>
      <span className={styles.detailLabel}>{label}:</span>
      <span className={styles.detailValue}>{value}</span>
    </div>
  )
}

function RoutineStep({ step, index }) {
  return (
    <li className={styles.step}>
      <span className={styles.stepName}>{step.step}</span>
      <span className={styles.stepProduct}>{step.product_type}</span>
      {step.category && <StepDetail label="Category" value={step.category} />}
      {step.percentage && <StepDetail label="Percentage" value={step.percentage} />}
      {step.concentration && <StepDetail label="Concentration" value={step.concentration} />}
      {step.toner_type && <StepDetail label="Toner type" value={step.toner_type} />}
      {step.moisturizer_type && <StepDetail label="Moisturizer type" value={step.moisturizer_type} />}
      {step.ingredients && <StepDetail label="Key ingredients" value={step.ingredients} />}
      {step.product_details && (
        <StepDetail label="Details" value={step.product_details} />
      )}
      <span className={styles.stepReason}>{step.reason}</span>
    </li>
  )
}

export default function ResultsPage() {
  const location = useLocation()
  const navigate = useNavigate()
  const result = location.state?.result

  if (!result) {
    return (
      <div className={styles.page}>
        <div className={styles.card}>
          <p>No results to show. Please start from the home page and upload a skin photo.</p>
          <button type="button" className={styles.backBtn} onClick={() => navigate('/')}>
            Go back
          </button>
        </div>
      </div>
    )
  }

  const rec = result.recommendation || {}
  const skin = result.skin_analysis || {}
  const lab = result.lab_analysis || {}
  const weekly = rec.weekly_treatments || []
  const kb = result.knowledge_base || {}
  const possible = rec.possible_condition || []
  const why = rec.why || {}

  const [chatMessages, setChatMessages] = useState([])
  const [feedbackInput, setFeedbackInput] = useState('')
  const [feedbackLoading, setFeedbackLoading] = useState(false)
  const [feedbackError, setFeedbackError] = useState(null)

  const handleFeedbackSubmit = async (e) => {
    e.preventDefault()
    const msg = feedbackInput.trim()
    if (!msg || feedbackLoading) return
    setFeedbackLoading(true)
    setFeedbackError(null)
    setChatMessages((prev) => [...prev, { role: 'user', text: msg }])
    setFeedbackInput('')
    try {
      const routineSummary = rec.routine
        ? { steps: rec.routine.flatMap((b) => b.steps || []).map((s) => ({ step: s.step, product_type: s.product_type })) }
        : null
      const data = await sendFeedback(msg, routineSummary)
      setChatMessages((prev) => [...prev, { role: 'assistant', text: data.reply }])
    } catch (err) {
      setFeedbackError(err.message)
      setChatMessages((prev) => [...prev, { role: 'assistant', text: `Sorry: ${err.message}` }])
    } finally {
      setFeedbackLoading(false)
    }
  }

  return (
    <div className={styles.page}>
      <button type="button" className={styles.backBtn} onClick={() => navigate('/')}>
        ← New analysis
      </button>

      {rec.severe_symptoms && (
        <div className={styles.urgent} role="alert">
          Possible severe symptoms were described. See a dermatologist or urgent care now. This app cannot treat bleeding, spreading infection, fever, or severe pain.
        </div>
      )}

      <section className={styles.card}>
        <div className={styles.titleRow}>
          <h2 className={styles.title}>Possible condition</h2>
          <span className={`${styles.badge} ${styles['badge' + (rec.confidence_level || 'Low')]}`}>
            Confidence: {rec.confidence_level || 'Low'}
          </span>
        </div>
        <ul className={styles.possibleList}>
          {(possible.length ? possible : ['Insufficient data for a named match']).map((p) => (
            <li key={p}>{p}</li>
          ))}
        </ul>
        <div className={styles.why}>
          <p><strong>Symptom matches:</strong> {(why.symptom_matches || []).join(', ') || '—'}</p>
          <p><strong>Skin type correlation:</strong> {why.skin_type_correlation || `Described as ${skin.skin_type || '—'}`}</p>
          <p><strong>Blood correlation:</strong> {why.blood_correlation || 'None used.'}</p>
        </div>
        {skin.prediction_uncertain && (
          <p className={styles.uncertain}>Photo prediction confidence is below 70% — treat the image label as uncertain.</p>
        )}
        <p className={styles.explanation}>{skin.explanation}</p>
      </section>

      <SkinRecommendation knowledge={kb} fallbackMessage="I don't have enough information in my built-in skincare database for this concern yet." />

      {(lab.values && Object.keys(lab.values).length > 0) || (lab.recommended_tests && lab.recommended_tests.length > 0) ? (
        <section className={styles.card}>
          <h2 className={styles.title}>Lab values (from report)</h2>
          <p className={styles.hint}>{lab.explanation}</p>
          {lab.recommended_tests && lab.recommended_tests.length > 0 && (
            <div className={styles.recommendedTests}>
              <h3 className={styles.recommendedTitle}>Tests used for skin-related analysis (all are considered when present)</h3>
              <ul className={styles.recommendedList}>
                {lab.recommended_tests.map((t, i) => (
                  <li key={i}>{t}</li>
                ))}
              </ul>
            </div>
          )}
          {lab.values && Object.keys(lab.values).length > 0 && (
            <>
              <h3 className={styles.foundTitle}>Found in your report</h3>
              <ul className={styles.labList}>
                {Object.entries(lab.values).map(([name, obj]) => (
                  <li key={name}>
                    <strong>{name.replace(/_/g, ' ')}:</strong> {obj.value} {obj.unit}
                  </li>
                ))}
              </ul>
            </>
          )}
        </section>
      ) : null}

      <section className={styles.card}>
        <h2 className={styles.title}>Your customized skincare routine</h2>
        <p className={styles.explanation}>{rec.explanation}</p>

        {rec.routine?.map((block) => (
          <div key={block.time} className={styles.routineBlock}>
            <h3 className={styles.time}>{block.time}</h3>
            <ol className={styles.steps}>
              {block.steps?.map((step, i) => (
                <RoutineStep key={i} step={step} index={i} />
              ))}
            </ol>
          </div>
        ))}

        {weekly.length > 0 && (
          <div className={styles.weeklySection}>
            <h3 className={styles.weeklyTitle}>Weekly face masks & procedures</h3>
            <p className={styles.weeklyIntro}>Use these in addition to your daily routine for best results.</p>
            <ul className={styles.weeklyList}>
              {weekly.map((item, i) => (
                <li key={i} className={styles.weeklyItem}>
                  <span className={styles.weeklyName}>{item.name}</span>
                  <span className={styles.weeklyType}>{item.type}</span>
                  <span className={styles.weeklyFreq}>{item.frequency}</span>
                  <span className={styles.weeklyDetails}>{item.details}</span>
                  <span className={styles.weeklyReason}>{item.reason}</span>
                </li>
              ))}
            </ul>
          </div>
        )}

        {rec.lifestyle?.length > 0 && (
          <div className={styles.labNotes}>
            <h3 className={styles.labNotesTitle}>Lifestyle / internal factors</h3>
            <ul>
              {rec.lifestyle.map((note, i) => (
                <li key={i}>{note}</li>
              ))}
            </ul>
          </div>
        )}

        {rec.when_to_see_dermatologist?.length > 0 && (
          <div className={styles.labNotes}>
            <h3 className={styles.labNotesTitle}>When to see a dermatologist</h3>
            <ul>
              {rec.when_to_see_dermatologist.map((note, i) => (
                <li key={i}>{note}</li>
              ))}
            </ul>
          </div>
        )}

        {rec.lab_notes?.length > 0 && (
          <div className={styles.labNotes}>
            <h3 className={styles.labNotesTitle}>Notes from your lab report</h3>
            <ul>
              {rec.lab_notes.map((note, i) => (
                <li key={i}>{note}</li>
              ))}
            </ul>
          </div>
        )}

        <div className={styles.disclaimerBlock}>
          <strong>Disclaimer:</strong> {rec.disclaimer}
        </div>

        <div className={styles.feedbackSection}>
          <h3 className={styles.feedbackTitle}>Feedback & adjustments</h3>
          <p className={styles.feedbackHint}>
            Share appreciation, or tell us if an ingredient doesn&apos;t suit you or isn&apos;t available. We&apos;ll say if it can be ignored (optional) or suggest an alternative.
          </p>
          <div className={styles.chatMessages}>
            {chatMessages.length === 0 && (
              <div className={styles.chatPlaceholder}>
                e.g. &quot;Thanks!&quot; or &quot;Niacinamide doesn&apos;t suit me&quot; / &quot;Vitamin C is not available here&quot;
              </div>
            )}
            {chatMessages.map((m, i) => (
              <div key={i} className={m.role === 'user' ? styles.chatBubbleUser : styles.chatBubbleBot}>
                {m.role === 'user' ? m.text : formatReply(m.text)}
              </div>
            ))}
          </div>
          <form onSubmit={handleFeedbackSubmit} className={styles.feedbackForm}>
            <input
              type="text"
              className={styles.feedbackInput}
              placeholder="Type your message…"
              value={feedbackInput}
              onChange={(e) => setFeedbackInput(e.target.value)}
              disabled={feedbackLoading}
            />
            <button type="submit" className={styles.feedbackSubmit} disabled={feedbackLoading || !feedbackInput.trim()}>
              {feedbackLoading ? 'Sending…' : 'Send'}
            </button>
          </form>
          {feedbackError && <div className={styles.feedbackError}>{feedbackError}</div>}
        </div>
      </section>
    </div>
  )
}
