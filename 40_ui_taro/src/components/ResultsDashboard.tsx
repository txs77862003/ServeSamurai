"use client"

import React from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Progress } from "@/components/ui/progress"
import { Badge } from "@/components/ui/badge"
import { Separator } from "@/components/ui/separator"
import { AnalysisResult, SimilarityResult } from "@/lib/analysis/serveAnalysis"
import { formatPercent } from "@/lib/utils"

type Props = {
  result: AnalysisResult
  videoUrl: string
}

export default function ResultsDashboard({ result, videoUrl }: Props) {
  const { similarities, advice } = result
  const top: SimilarityResult | undefined = similarities[0]

  return (
    <div className="grid grid-cols-1 lg:grid-cols-5 gap-6">
      <Card className="lg:col-span-3">
        <CardHeader>
          <CardTitle>Your Serve Playback</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="aspect-video w-full overflow-hidden rounded-md border">
            <video src={videoUrl} className="h-full w-full" controls playsInline />
          </div>
          <p className="mt-3 text-sm text-muted-foreground">Detected key moments: toss → contact → follow-through. Metrics are approximations from optical motion.</p>
        </CardContent>
      </Card>

      <Card className="lg:col-span-2">
        <CardHeader>
          <CardTitle>Similarity to Pros</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          {similarities.map((s) => (
            <div key={s.player} className="space-y-2">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Badge variant={s.player === top?.player ? "default" : "secondary"}>{s.player}</Badge>
                  {s.player === top?.player && (
                    <span className="text-xs text-muted-foreground">closest match</span>
                  )}
                </div>
                <span className="text-sm font-medium">{formatPercent(s.score)}</span>
              </div>
              <Progress value={s.score} />
            </div>
          ))}
          <Separator />
          <div>
            <p className="text-sm font-medium mb-2">What this means</p>
            <p className="text-sm text-muted-foreground">Higher percentage indicates your movement patterns are closer to the selected player across leg drive, shoulder rotation, and racquet drop proxies.</p>
          </div>
        </CardContent>
      </Card>

      <Card className="lg:col-span-5">
        <CardHeader>
          <CardTitle>Targeted Advice</CardTitle>
        </CardHeader>
        <CardContent>
          {advice.length ? (
            <ul className="list-disc pl-5 space-y-2">
              {advice.map((tip, i) => (
                <li key={i} className="text-sm leading-relaxed">{tip}</li>
              ))}
            </ul>
          ) : (
            <p className="text-sm text-muted-foreground">Upload a video to receive specific pointers.</p>
          )}
        </CardContent>
      </Card>

      <Card className="lg:col-span-5">
        <CardHeader>
          <CardTitle>Visual References</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 sm:grid-cols-4 gap-4">
            {["Nishikori", "Federer", "Djokovic", "Alcaraz"].map((name) => (
              <figure key={name} className="space-y-2">
                <img
                  src={`https://images.unsplash.com/photo-1519681393784-d120267933ba?q=80&w=800&auto=format&fit=crop`}
                  alt={`${name} reference`}
                  className="w-full h-44 object-cover rounded-md border"
                />
                <figcaption className="text-sm text-muted-foreground">Representative still for {name} (for study; not actual footage)</figcaption>
              </figure>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  )
}