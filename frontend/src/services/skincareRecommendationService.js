/**
 * Local skincare matcher. Uses only skinKnowledgeBase.json — no internet.
 */
import knowledgeBase from '../data/skinKnowledgeBase.json'

export const UNKNOWN_MESSAGE =
  "I don't have enough information in my built-in skincare database for this concern yet."

const STRONG_ACTIVES = ['retinol', 'adapalene', 'glycolic acid', 'lactic acid', 'salicylic acid']
const RETINOIDS = ['retinol', 'adapalene']
const ACIDS = ['glycolic acid', 'lactic acid', 'salicylic acid']

export function getKnowledgeBase() {
  return knowledgeBase
}

function normalize(text) {
  return String(text || '')
    .toLowerCase()
    .replace(/[’]/g, "'")
    .replace(/[^a-z0-9\s'-]/g, ' ')
    .replace(/\s+/g, ' ')
    .trim()
}

function allergyBlocked(ingredientName, sensitivities) {
  const n = normalize(sensitivities)
  const ing = normalize(ingredientName)
  if (!n || !ing) return false
  if (n.includes(ing)) return true
  return ing.split(' ').some((tok) => tok.length >= 4 && new RegExp(`\\b${tok}\\b`).test(n))
}

function scoreConcern(text, key, concern) {
  if (!text) return 0
  let score = 0
  const name = normalize(concern.name)
  if (name && text.includes(name)) score += 4
  const keyPhrase = key.replace(/_/g, ' ')
  if (keyPhrase && text.includes(keyPhrase)) score += 3
  const aliases = (concern.aliases || []).map(normalize).sort((a, b) => b.length - a.length)
  for (const alias of aliases) {
    if (alias.length < 3) continue
    if (text.includes(alias)) score += alias.includes(' ') ? 3 : 2
  }
  return score
}

function scoreLabels(labels, key, concern) {
  let score = 0
  const names = new Set([normalize(concern.name), key.replace(/_/g, ' '), normalize(key)])
  const aliases = new Set((concern.aliases || []).map(normalize))
  for (const raw of labels || []) {
    const lab = normalize(raw)
    if (!lab) continue
    if (names.has(lab) || aliases.has(lab)) {
      score += 5
      continue
    }
    for (const n of names) {
      if (lab.length >= 4 && (n.includes(lab) || lab.includes(n))) score += 4
    }
  }
  return score
}

function limitStrongActives(ingredients) {
  let hasRetinoid = false
  let hasAcid = false
  const kept = []
  for (const ing of ingredients) {
    const n = normalize(ing.name)
    const isRetinoid = RETINOIDS.some((r) => n.includes(r))
    const isAcid = ACIDS.some((a) => n.includes(a))
    if (isRetinoid && hasAcid) continue
    if (isAcid && hasRetinoid) continue
    if (isAcid && hasAcid) continue
    if (isRetinoid && hasRetinoid) continue
    if (isRetinoid) hasRetinoid = true
    if (isAcid) hasAcid = true
    kept.push(ing)
  }
  return kept
}

/**
 * @param {string} userInput
 * @param {{ extraConcerns?: string[], sensitivities?: string, usesActives?: string }} [options]
 */
export function getSkincareRecommendations(userInput, options = {}) {
  const text = normalize(userInput)
  const extras = options.extraConcerns || []
  const sensitivities = options.sensitivities || ''
  const uses = normalize(options.usesActives || '')

  const matches = []
  for (const [key, concern] of Object.entries(knowledgeBase)) {
    const score = scoreConcern(text, key, concern) + scoreLabels(extras, key, concern)
    if (score > 0) matches.push({ key, score, concern })
  }
  matches.sort((a, b) => b.score - a.score)
  const top = matches.filter((m) => m.score >= 2).slice(0, 4)

  if (!top.length && !text && !extras.length) {
    return {
      detectedConcerns: [],
      recommendedIngredients: [],
      unknown: true,
      message: 'Insufficient data for a safe recommendation.',
      warnings: [],
      source: 'local_knowledge_base',
    }
  }

  if (!top.length) {
    return {
      detectedConcerns: [],
      recommendedIngredients: [],
      unknown: true,
      message: UNKNOWN_MESSAGE,
      warnings: [],
      source: 'local_knowledge_base',
    }
  }

  const collected = []
  const detectedConcerns = []
  const warnings = []

  for (const { key, score, concern } of top) {
    detectedConcerns.push({
      id: key,
      name: concern.name,
      description: concern.description,
      matchScore: score,
    })
    for (const w of concern.warnings || []) {
      if (!warnings.includes(w)) warnings.push(w)
    }
    for (const ing of concern.ingredients || []) {
      const priority = Number(ing.priority || 99)
      collected.push({
        ...ing,
        concern: concern.name,
        rankScore: score * 10 + (10 - Math.min(priority, 10)),
      })
    }
  }

  const byName = new Map()
  for (const item of collected) {
    if (allergyBlocked(item.name, sensitivities)) continue
    const k = normalize(item.name)
    const prev = byName.get(k)
    if (!prev || item.rankScore > prev.rankScore) byName.set(k, item)
  }

  let ingredients = limitStrongActives(
    [...byName.values()].sort((a, b) => b.rankScore - a.rankScore || a.priority - b.priority)
  )

  if (uses === 'yes' || uses === 'sometimes') {
    warnings.push(
      'You already use actives. Avoid adding another strong active in the same routine.'
    )
    const filtered = ingredients.filter(
      (ing) => !STRONG_ACTIVES.some((s) => normalize(ing.name).includes(s))
    )
    if (filtered.length) ingredients = filtered
  }

  const skipped = [...new Set(collected.filter((i) => allergyBlocked(i.name, sensitivities)).map((i) => i.name))]
  if (skipped.length) {
    warnings.push(`Skipped because of your listed sensitivity/allergy: ${skipped.join(', ')}.`)
  }

  return {
    detectedConcerns,
    recommendedIngredients: ingredients.slice(0, 8).map((i) => ({
      name: i.name,
      benefit: i.benefit,
      priority: i.priority,
      usage: i.usage || '',
      caution: i.caution || '',
      concern: i.concern || '',
    })),
    unknown: false,
    message: '',
    warnings,
    source: 'local_knowledge_base',
  }
}
