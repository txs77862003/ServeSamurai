"use client"

import React, { useCallback, useMemo, useRef, useState } from "react"
import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"
import { cn } from "@/lib/utils"

const ACCEPTED_TYPES = ["video/mp4", "video/webm", "video/quicktime"]
const MAX_BYTES = 50 * 1024 * 1024 // 50MB

type Props = {
  onVideoReady: (file: File, objectUrl: string) => void
}

export default function UploadDropzone({ onVideoReady }: Props) {
  const [dragActive, setDragActive] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const inputRef = useRef<HTMLInputElement>(null)

  const onClick = () => inputRef.current?.click()

  const validate = useCallback((file: File) => {
    if (!ACCEPTED_TYPES.includes(file.type)) {
      return `Unsupported file type. Use MP4, WEBM, or MOV.`
    }
    if (file.size > MAX_BYTES) {
      return `File too large. Max size is 50MB.`
    }
    return null
  }, [])

  const handleFiles = useCallback(
    (files?: FileList | null) => {
      if (!files || !files.length) return
      const file = files[0]
      const err = validate(file)
      if (err) {
        setError(err)
        return
      }
      setError(null)
      const url = URL.createObjectURL(file)
      onVideoReady(file, url)
    },
    [onVideoReady, validate]
  )

  const onDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault()
      e.stopPropagation()
      setDragActive(false)
      handleFiles(e.dataTransfer?.files)
    },
    [handleFiles]
  )

  const onDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(true)
  }, [])

  const onDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false)
  }, [])

  const helperText = useMemo(() => {
    return error ?? "Drag & drop a serve video here, or click to browse."
  }, [error])

  return (
    <Card className={cn("border-dashed", dragActive && "border-primary")}
      onDrop={onDrop}
      onDragOver={onDragOver}
      onDragLeave={onDragLeave}
    >
      <CardContent className="p-6">
        <div className="flex flex-col items-center justify-center gap-4 py-10 text-center">
          <div className="w-full max-w-md">
            <div
              onClick={onClick}
              className={cn(
                "cursor-pointer rounded-md border border-dashed p-8",
                dragActive ? "bg-accent" : "bg-secondary"
              )}
            >
              <p className="text-sm text-muted-foreground">
                {helperText}
              </p>
              <p className="mt-2 text-xs text-muted-foreground">Accepted: mp4, webm, mov. Max 50MB.</p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <Button onClick={onClick} variant="default">Choose File</Button>
            <input
              ref={inputRef}
              className="hidden"
              type="file"
              accept={ACCEPTED_TYPES.join(",")}
              onChange={(e) => handleFiles(e.target.files)}
            />
          </div>
          {error && (
            <p className="text-destructive text-sm" role="alert">{error}</p>
          )}
        </div>
      </CardContent>
    </Card>
  )
}