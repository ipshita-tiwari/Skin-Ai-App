import { Outlet } from 'react-router-dom'
import Disclaimer from './Disclaimer'
import styles from './Layout.module.css'

export default function Layout({ children }) {
  return (
    <div className={styles.wrapper}>
      <header className={styles.header}>
        <h1 className={styles.logo}>SkinAI</h1>
        <p className={styles.tagline}>Evidence-style skincare guidance from your description, photo, and optional labs</p>
      </header>
      <main className={styles.main}>
        {children || <Outlet />}
      </main>
      <Disclaimer />
      <footer className={styles.footer}>
        <span>Not medical advice. For informational use only.</span>
      </footer>
    </div>
  )
}
