"use client"
import * as React from 'react'

type Props = {
  data: number[]
  width?: number
  height?: number
  stroke?: string
  fill?: string
}

export default function Sparkline({ data, width = 120, height = 36, stroke = '#16a34a', fill = 'transparent' }: Props) {
  if (!data || data.length === 0) {
    return <svg width={width} height={height} />
  }
  const min = Math.min(...data)
  const max = Math.max(...data)
  const norm = (v: number) => max === min ? height / 2 : height - ((v - min) / (max - min)) * height
  const step = data.length > 1 ? width / (data.length - 1) : width
  const points = data.map((v, i) => `${i * step},${norm(v)}`).join(' ')
  return (
    <svg width={width} height={height} viewBox={`0 0 ${width} ${height}`}>
      <polyline points={points} fill={fill} stroke={stroke} strokeWidth={1.5} vectorEffect="non-scaling-stroke" />
    </svg>
  )
}

