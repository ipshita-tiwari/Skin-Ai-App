import styles from './SkinRecommendation.module.css'

export default function SkinRecommendation({ knowledge, fallbackMessage }) {
  if (!knowledge) return null

  const concerns = knowledge.detected_concerns || knowledge.detectedConcerns || []
  const ingredients = knowledge.recommended_ingredients || knowledge.recommendedIngredients || []
  const unknown = knowledge.unknown
  const message = knowledge.message
  const warnings = knowledge.warnings || knowledge.knowledge_warnings || []

  return (
    <section className={styles.wrap} aria-label="Built-in ingredient recommendations">
      <h2 className={styles.title}>Built-in ingredient match</h2>
      <p className={styles.source}>From the local skincare knowledge base — not the internet.</p>

      {unknown || (!concerns.length && !ingredients.length) ? (
        <p className={styles.unknown}>{message || fallbackMessage}</p>
      ) : (
        <>
          <h3 className={styles.sub}>Detected concerns</h3>
          <ul className={styles.concerns}>
            {concerns.map((c) => (
              <li key={c.id || c.name} className={styles.chip}>
                {c.name}
              </li>
            ))}
          </ul>

          <h3 className={styles.sub}>Recommended ingredients</h3>
          <ol className={styles.list}>
            {ingredients.map((ing, i) => (
              <li key={`${ing.name}-${i}`} className={styles.item}>
                <div className={styles.nameRow}>
                  <span className={styles.index}>{i + 1}</span>
                  <strong>{ing.name}</strong>
                </div>
                <p className={styles.benefit}>{ing.benefit}</p>
                {ing.usage ? <p className={styles.meta}>{ing.usage}</p> : null}
                {ing.caution ? <p className={styles.caution}>{ing.caution}</p> : null}
              </li>
            ))}
          </ol>
        </>
      )}

      {warnings.length > 0 && (
        <ul className={styles.warnList}>
          {warnings.map((w, i) => (
            <li key={i}>{w}</li>
          ))}
        </ul>
      )}
    </section>
  )
}
