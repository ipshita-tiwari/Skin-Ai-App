import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { analyzeSkin } from '../api/client'
import styles from './HomePage.module.css'

const SKIN_TYPES = [
  { value: '', label: 'Select…' },
  { value: 'dry', label: 'Dry' },
  { value: 'oily', label: 'Oily' },
  { value: 'combination', label: 'Combination' },
  { value: 'normal', label: 'Normal' },
  { value: 'sensitive', label: 'Sensitive' },
  { value: 'not sure', label: 'Not sure' },
]

const CONCERNS = [
  { id: 'acne', label: 'Acne' },
  { id: 'dryness', label: 'Dryness' },
  { id: 'dehydrated skin', label: 'Dehydration' },
  { id: 'oiliness', label: 'Oiliness' },
  { id: 'dullness', label: 'Dullness' },
  { id: 'redness', label: 'Redness' },
  { id: 'sensitive skin', label: 'Sensitive skin' },
  { id: 'dark spots', label: 'Dark spots' },
  { id: 'uneven skin tone', label: 'Uneven tone' },
  { id: 'blackheads', label: 'Blackheads' },
  { id: 'whiteheads', label: 'Whiteheads' },
  { id: 'enlarged-looking pores', label: 'Visible pores' },
  { id: 'fine lines', label: 'Fine lines' },
  { id: 'rough texture', label: 'Rough texture' },
]

const USES_ACTIVES = [
  { value: '', label: 'Select…' },
  { value: 'yes', label: 'Yes' },
  { value: 'no', label: 'No' },
  { value: 'sometimes', label: 'Sometimes' },
]

export default function HomePage() {
  const navigate = useNavigate()
  const [skinFile, setSkinFile] = useState(null)
  const [bloodFile, setBloodFile] = useState(null)
  const [textInput, setTextInput] = useState('')
  const [skinTypeSelf, setSkinTypeSelf] = useState('')
  const [concernsChecked, setConcernsChecked] = useState({})
  const [usesActives, setUsesActives] = useState('')
  const [sensitivities, setSensitivities] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  const hasPhoto = !!skinFile
  const hasText = textInput.trim() || skinTypeSelf
  const canSubmit = hasPhoto || hasText

  const handleConcernChange = (id) => {
    setConcernsChecked((prev) => ({ ...prev, [id]: !prev[id] }))
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!canSubmit) {
      setError('Please either upload a skin photo or describe your skin / answer the questions below.')
      return
    }
    setLoading(true)
    setError(null)
    const concernsStr = Object.entries(concernsChecked)
      .filter(([, v]) => v)
      .map(([k]) => CONCERNS.find((c) => c.id === k)?.label || k)
      .join(', ')
    const textPayload = {
      text_input: textInput.trim() || undefined,
      skin_type_self: skinTypeSelf || undefined,
      concerns: concernsStr || undefined,
      uses_actives: usesActives || undefined,
      sensitivities: sensitivities.trim() || undefined,
    }
    try {
      const result = await analyzeSkin(skinFile || null, bloodFile || null, textPayload)
      navigate('/results', { state: { result } })
    } catch (err) {
      setError(err.message || 'Something went wrong. Please try again.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className={styles.page}>
      <section className={styles.card}>
        <p className={styles.kicker}>Educational guidance · not a diagnosis</p>
        <h2 className={styles.title}>Build a calmer, clearer routine</h2>
        <p className={styles.hint}>
          Describe how your skin feels in your own words. The app matches concerns to a <strong>built-in ingredient database</strong> (no web search). You can also add a photo or an optional lab report.
        </p>

        <form onSubmit={handleSubmit} className={styles.form}>
          {/* Uploads */}
          <div className={styles.section}>
            <h3 className={styles.sectionTitle}>Option 1: Upload (optional)</h3>
            <div className={styles.field}>
              <label htmlFor="skin-image">Skin photo</label>
              <input
                id="skin-image"
                type="file"
                accept="image/jpeg,image/png,image/webp"
                onChange={(e) => { setSkinFile(e.target.files?.[0] || null); setError(null) }}
                disabled={loading}
              />
              <span className={styles.fileName}>{skinFile ? skinFile.name : 'No file chosen'}</span>
            </div>
            <div className={styles.field}>
              <label htmlFor="blood-report">Blood report (optional)</label>
              <input
                id="blood-report"
                type="file"
                accept="application/pdf,image/jpeg,image/png,image/webp"
                onChange={(e) => { setBloodFile(e.target.files?.[0] || null); setError(null) }}
                disabled={loading}
              />
              <span className={styles.fileName}>{bloodFile ? bloodFile.name : 'No file chosen'}</span>
              <span className={styles.testsHint}>
                Recommended: CBC, Vitamin D, B12, Iron/Ferritin, Fasting glucose or HbA1c, TSH/T3/T4, Testosterone, DHEAS, Prolactin, LH, FSH, Fasting insulin.
              </span>
            </div>
          </div>

          {/* Chat + questions */}
          <div className={styles.section}>
            <h3 className={styles.sectionTitle}>Option 2: Describe your skin (no photo needed)</h3>
            <div className={styles.field}>
              <label htmlFor="chat">Describe your skin or problems</label>
              <textarea
                id="chat"
                className={styles.chatBox}
                placeholder="e.g. I have dry, flaky skin and some redness. I get breakouts sometimes."
                value={textInput}
                onChange={(e) => { setTextInput(e.target.value); setError(null) }}
                disabled={loading}
                rows={4}
              />
            </div>
            <p className={styles.questionsIntro}>Answer these so we can tailor the routine (only a few):</p>
            <div className={styles.field}>
              <label htmlFor="skin-type">What best describes your skin?</label>
              <select
                id="skin-type"
                className={styles.select}
                value={skinTypeSelf}
                onChange={(e) => setSkinTypeSelf(e.target.value)}
                disabled={loading}
              >
                {SKIN_TYPES.map((opt) => (
                  <option key={opt.value || 'empty'} value={opt.value}>{opt.label}</option>
                ))}
              </select>
            </div>
            <div className={styles.field}>
              <label>Main concerns (select all that apply)</label>
              <div className={styles.checkboxGroup}>
                {CONCERNS.map((c) => (
                  <label key={c.id} className={styles.checkboxLabel}>
                    <input
                      type="checkbox"
                      checked={!!concernsChecked[c.id]}
                      onChange={() => handleConcernChange(c.id)}
                      disabled={loading}
                    />
                    <span>{c.label}</span>
                  </label>
                ))}
              </div>
            </div>
            <div className={styles.field}>
              <label htmlFor="uses-actives">Do you use retinol, vitamin C, or AHA/BHA?</label>
              <select
                id="uses-actives"
                className={styles.select}
                value={usesActives}
                onChange={(e) => setUsesActives(e.target.value)}
                disabled={loading}
              >
                {USES_ACTIVES.map((opt) => (
                  <option key={opt.value || 'empty'} value={opt.value}>{opt.label}</option>
                ))}
              </select>
            </div>
            <div className={styles.field}>
              <label htmlFor="sensitivities">Any sensitivities or allergies?</label>
              <input
                id="sensitivities"
                type="text"
                className={styles.textInput}
                placeholder="e.g. fragrance, nickel, or leave blank"
                value={sensitivities}
                onChange={(e) => setSensitivities(e.target.value)}
                disabled={loading}
              />
            </div>
          </div>

          {error && (
            <div className={styles.error} role="alert">
              {error}
            </div>
          )}

          <button
            type="submit"
            className={styles.submit}
            disabled={loading || !canSubmit}
          >
            {loading ? (
              <span className={styles.loadingInner}>
                <span className={styles.spinner} aria-hidden="true" />
                Matching your concerns…
              </span>
            ) : (
              'Get my routine'
            )}
          </button>
        </form>
      </section>
    </div>
  )
}
