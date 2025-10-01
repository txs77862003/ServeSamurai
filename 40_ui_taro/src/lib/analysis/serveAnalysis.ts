export type ServeFeatures = {
  durationMs: number
  motionEnergy: number[]
  centroidPath: { x: number; y: number }[]
  peakTossIndex: number
  contactIndex: number
  followThroughIndex: number
  lowerBodyEngagement: number
  shoulderRotationProxy: number
  racquetDropProxy: number
}

export type PlayerProfile = {
  name: string
  refs: Partial<ServeFeatures>
}

export type SimilarityResult = {
  player: string
  score: number
  deltas: Record<string, number>
}

export type AnalysisResult = {
  features: ServeFeatures
  similarities: SimilarityResult[]
  advice: string[]
}

const clamp = (v: number, min = 0, max = 1) => Math.max(min, Math.min(max, v))

const PROFILES: PlayerProfile[] = [
  { name: "Nishikori", refs: { lowerBodyEngagement: 0.65, shoulderRotationProxy: 0.6, racquetDropProxy: 0.55 } },
  { name: "Federer", refs: { lowerBodyEngagement: 0.75, shoulderRotationProxy: 0.8, racquetDropProxy: 0.85 } },
  { name: "Djokovic", refs: { lowerBodyEngagement: 0.85, shoulderRotationProxy: 0.7, racquetDropProxy: 0.7 } },
  { name: "Alcaraz", refs: { lowerBodyEngagement: 0.88, shoulderRotationProxy: 0.82, racquetDropProxy: 0.8 } },
]

export async function extractServeFeatures(
  video: HTMLVideoElement,
  opts: { sampleFps?: number } = {}
): Promise<ServeFeatures> {
  const sampleFps = opts.sampleFps ?? 12
  await ensureVideoReady(video)

  const durationMs = video.duration * 1000
  const sampleCount = Math.max(8, Math.floor(video.duration * sampleFps))

  const canvas = document.createElement("canvas")
  const ctx = canvas.getContext("2d", { willReadFrequently: true })
  if (!ctx) throw new Error("Canvas 2D not available")

  canvas.width = Math.floor(video.videoWidth / 4) || 160
  canvas.height = Math.floor(video.videoHeight / 4) || 90

  const motionEnergy: number[] = []
  const centroidPath: { x: number; y: number }[] = []
  let prev: Uint8ClampedArray | null = null

  for (let i = 0; i < sampleCount; i++) {
    const t = (i / sampleCount) * video.duration
    await seekVideo(video, t)
    ctx.drawImage(video, 0, 0, canvas.width, canvas.height)
    const { data, width, height } = ctx.getImageData(0, 0, canvas.width, canvas.height)

    let diffSum = 0
    let cx = 0
    let cy = 0
    let mass = 0

    for (let p = 0; p < data.length; p += 4) {
      const r = data[p], g = data[p + 1], b = data[p + 2]
      const y = 0.2126 * r + 0.7152 * g + 0.0722 * b
      const idx = p / 4
      const xCoord = idx % width
      const yCoord = Math.floor(idx / width)

      let v = y
      if (prev) {
        const pr = prev[p], pg = prev[p + 1], pb = prev[p + 2]
        const py = 0.2126 * pr + 0.7152 * pg + 0.0722 * pb
        v = Math.abs(y - py)
      }

      const w = v
      diffSum += v
      mass += w
      cx += w * xCoord
      cy += w * yCoord
    }

    const normEnergy = clamp(diffSum / (width * height * 255))
    motionEnergy.push(normEnergy)

    if (mass > 0) {
      centroidPath.push({ x: cx / mass / width, y: cy / mass / height })
    } else {
      centroidPath.push({ x: 0.5, y: 0.5 })
    }

    prev = new Uint8ClampedArray(data)
  }

  const peakTossIndex = argMax(smooth(motionEnergy, 3))
  const contactIndex = Math.min(motionEnergy.length - 1, peakTossIndex + Math.max(1, Math.floor(sampleFps * 0.2)))
  const followThroughIndex = Math.min(motionEnergy.length - 1, contactIndex + Math.max(1, Math.floor(sampleFps * 0.3)))

  const lowerHalfMotion = average(centroidPath.map((c, i) => (c.y > 0.6 ? motionEnergy[i] : 0)))
  const upperHalfMotion = average(centroidPath.map((c, i) => (c.y <= 0.6 ? motionEnergy[i] : 0)))
  const leftMotion = average(centroidPath.map((c, i) => (c.x < 0.5 ? motionEnergy[i] : 0)))
  const rightMotion = average(centroidPath.map((c, i) => (c.x >= 0.5 ? motionEnergy[i] : 0)))

  const lowerBodyEngagement = clamp(lowerHalfMotion * 2)
  const shoulderRotationProxy = clamp(Math.abs(rightMotion - leftMotion) * 4)
  const racquetDropProxy = clamp(upperHalfMotion * 1.2)

  return {
    durationMs,
    motionEnergy: normalizeArray(motionEnergy),
    centroidPath,
    peakTossIndex,
    contactIndex,
    followThroughIndex,
    lowerBodyEngagement,
    shoulderRotationProxy,
    racquetDropProxy,
  }
}

export function compareToPros(features: ServeFeatures): SimilarityResult[] {
  return PROFILES.map((p) => {
    const deltas: Record<string, number> = {}
    let totalDelta = 0
    let totalWeight = 0

    const metrics: Array<{ key: keyof ServeFeatures; weight: number }> = [
      { key: "lowerBodyEngagement", weight: 1.2 },
      { key: "shoulderRotationProxy", weight: 1.1 },
      { key: "racquetDropProxy", weight: 1.0 },
    ]

    metrics.forEach(({ key, weight }) => {
      const ref = (p.refs as any)[key]
      if (typeof ref === "number") {
        const v = (features as any)[key] as number
        const d = Math.abs(v - ref)
        deltas[key] = d
        totalDelta += d * weight
        totalWeight += weight
      }
    })

    const avgDelta = totalWeight > 0 ? totalDelta / totalWeight : 1
    const score = clamp(1 - avgDelta) * 100

    return { player: p.name, score: Math.round(score), deltas }
  }).sort((a, b) => b.score - a.score)
}

export function generateAdvice(features: ServeFeatures, top: SimilarityResult) {
  const tips: string[] = []
  const profile = PROFILES.find((p) => p.name === top.player)!

  const advise = (key: keyof ServeFeatures, label: string, how: string, weight = 1) => {
    const ref = (profile.refs as any)[key] as number | undefined
    if (typeof ref === "number") {
      const cur = (features as any)[key] as number
      if (cur < ref) {
        const gap = ref - cur
        if (gap > 0.05 / weight) tips.push(`${label}: ${how}`)
      }
    }
  }

  advise("lowerBodyEngagement", "Use legs more in the loading phase", "Deeper knee bend and drive up through your hips to transfer energy into the toss and upward jump. Try a slow-count load: 1-2 load, 3 explode.", 1.2)
  advise("shoulderRotationProxy", "Add more shoulder and trunk rotation", "Turn your hitting shoulder behind you in the trophy position and uncoil through contact. Keep non-dominant arm up longer to create stretch.", 1.1)
  advise("racquetDropProxy", "Increase racquet drop", "Relax your wrist and let the elbow lead so the racquet head drops behind your back before driving up (the 'scratch your back' feel).", 1)

  if (tips.length === 0) {
    tips.push(`Great job — your mechanics resemble ${profile.name}. Focus on timing between toss, leg drive, and contact for even more efficiency.`)
  }
  return tips
}

export async function analyzeServe(video: HTMLVideoElement): Promise<AnalysisResult> {
  try {
    const pythonResult = await analyzeServeWithPython(video)
    if (pythonResult) return pythonResult
  } catch (error) {
    console.warn('Python analysis failed, falling back to JavaScript analysis:', error)
  }

  const features = await extractServeFeatures(video)
  const similarities = compareToPros(features)
  const advice = generateAdvice(features, similarities[0])
  return { features, similarities, advice }
}

async function analyzeServeWithPython(video: HTMLVideoElement): Promise<AnalysisResult | null> {
  try {
    const clippedVideosData = sessionStorage.getItem('clippedVideos')
    const segmentsData = sessionStorage.getItem('segments')
    if (!clippedVideosData || !segmentsData) throw new Error('クリッピング結果が見つかりません')

    const clippedVideos = JSON.parse(clippedVideosData)
    const segments = JSON.parse(segmentsData)
    const currentVideoPath = clippedVideos[0]?.path
    if (!currentVideoPath) throw new Error('動画パスが見つかりません')

    const requestData = { videoPath: currentVideoPath, segments }
    const response = await fetch('/api/analyze-serve', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(requestData) })
    if (!response.ok) throw new Error(`API request failed: ${response.status}`)
    const result = await response.json()

    try {
      if (result?.userCsv) sessionStorage.setItem('poseAdviceUserCsv', result.userCsv)
      if (result?.referenceSuggestions) sessionStorage.setItem('poseAdviceReferenceSuggestions', JSON.stringify(result.referenceSuggestions))
      if (result?.userClip) sessionStorage.setItem('poseAdviceUserClip', JSON.stringify(result.userClip))
    } catch {}

    if (result.success) {
      return {
        features: convertMockFeatures(result.analysis),
        similarities: convertSimilarityFromAPI(result.similarity),
        advice: result.analysis.recommendations || [],
      }
    }
    throw new Error(result.error || 'Unknown error')
  } catch (e) {
    console.error('Python analysis error:', e)
    return null
  }
}

function convertMockFeatures(mockAnalysis: any): ServeFeatures {
  return {
    durationMs: mockAnalysis.videoMetrics?.duration * 1000 || 2000,
    motionEnergy: [0.5, 0.6, 0.7, 0.8, 0.9, 0.8, 0.7, 0.6],
    centroidPath: [ { x: 0.5, y: 0.5 }, { x: 0.5, y: 0.5 }, { x: 0.5, y: 0.5 }, { x: 0.5, y: 0.5 } ],
    peakTossIndex: 3,
    contactIndex: 5,
    followThroughIndex: 7,
    lowerBodyEngagement: mockAnalysis.technique?.stance === 'Good' ? 0.7 : 0.5,
    shoulderRotationProxy: mockAnalysis.technique?.follow_through === 'Excellent' ? 0.8 : 0.6,
    racquetDropProxy: mockAnalysis.technique?.grip === 'Continental' ? 0.75 : 0.5,
  }
}

export type SimilarityAPIResult = { players: string[]; probabilities: Record<string, number>; top1: { player: string; score: number } }

function convertSimilarityFromAPI(sim: any): SimilarityResult[] {
  try {
    const api: SimilarityAPIResult = sim
    const entries = Object.entries(api.probabilities || {})
    const list: SimilarityResult[] = entries.map(([player, prob]) => ({
      player: player as any,
      score: Math.round(Number(prob) * 100),
      deltas: { lowerBodyEngagement: 0, shoulderRotationProxy: 0, racquetDropProxy: 0 },
    }))
    return list.sort((a, b) => b.score - a.score)
  } catch {
    return []
  }
}

function convertMockSimilarities(mockAnalysis: any): SimilarityResult[] {
  const baseScore = mockAnalysis.accuracy || 85
  const arr = [
    { player: 'Nishikori', score: Math.min(100, baseScore + Math.floor(Math.random() * 10) - 5), deltas: { lowerBodyEngagement: 0.1, shoulderRotationProxy: 0.05, racquetDropProxy: 0.08 } },
    { player: 'Federer',  score: Math.min(100, baseScore + Math.floor(Math.random() * 10) - 5), deltas: { lowerBodyEngagement: 0.08, shoulderRotationProxy: 0.12, racquetDropProxy: 0.06 } },
    { player: 'Djokovic', score: Math.min(100, baseScore + Math.floor(Math.random() * 10) - 5), deltas: { lowerBodyEngagement: 0.06, shoulderRotationProxy: 0.09, racquetDropProxy: 0.10 } },
    { player: 'Alcaraz',  score: Math.min(100, baseScore + Math.floor(Math.random() * 10) - 5), deltas: { lowerBodyEngagement: 0.07, shoulderRotationProxy: 0.11, racquetDropProxy: 0.09 } },
  ].sort((a, b) => b.score - a.score)
  return arr as any as SimilarityResult[]
}

function normalizeArray(arr: number[]) { const max = Math.max(1e-6, ...arr); return arr.map((v) => v / max) }
function smooth(arr: number[], w = 3) { const out: number[] = []; for (let i = 0; i < arr.length; i++) { let s = 0, c = 0; for (let j = -w; j <= w; j++) { const k = i + j; if (k >= 0 && k < arr.length) { s += arr[k]; c++; } } out.push(s / c) } return out }
function argMax(arr: number[]) { let idx = 0; for (let i = 1; i < arr.length; i++) if (arr[i] > arr[idx]) idx = i; return idx }
function average(arr: number[]) { if (!arr.length) return 0; return arr.reduce((a, b) => a + b, 0) / arr.length }
function ensureVideoReady(video: HTMLVideoElement) { return new Promise<void>((resolve) => { if (video.readyState >= 2 && video.duration) return resolve(); const onLoaded = () => { cleanup(); resolve(); }; const cleanup = () => { video.removeEventListener("loadedmetadata", onLoaded); video.removeEventListener("canplay", onLoaded) }; video.addEventListener("loadedmetadata", onLoaded); video.addEventListener("canplay", onLoaded) }) }
function seekVideo(video: HTMLVideoElement, time: number) { return new Promise<void>((resolve) => { const onSeeked = () => { video.removeEventListener("seeked", onSeeked); resolve() }; video.addEventListener("seeked", onSeeked); video.currentTime = Math.min(Math.max(time, 0), Math.max(0.001, video.duration - 0.001)) }) }

// (Named exports are already declared above via `export function` / `export type`.)
