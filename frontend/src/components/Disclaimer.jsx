/**
 * Visible disclaimer that the app does not provide medical advice.
 * Shown on every page for compliance and user safety.
 */
import styles from './Disclaimer.module.css'

export default function Disclaimer() {
  return (
    <aside className={styles.disclaimer} role="complementary" aria-label="Medical disclaimer">
      <strong>Disclaimer:</strong> This tool does not provide medical advice. It is for
      informational and educational purposes only. Always seek the advice of a dermatologist
      or other qualified healthcare provider with any questions about your skin or health.
    </aside>
  )
}
