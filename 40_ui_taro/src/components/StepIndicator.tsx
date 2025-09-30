'use client';

import React from 'react';
import Link from 'next/link';
import { Card, CardContent } from '@/components/ui/card';

interface StepIndicatorProps {
  currentStep: number;
}

export default function StepIndicator({ currentStep }: StepIndicatorProps) {
  const steps = [
    { number: 1, title: 'Video Upload', path: '/' },
    { number: 2, title: 'Manual Clipping', path: '/manual-clip' },
    { number: 3, title: 'Results Display', path: '/results' },
    { number: 4, title: 'Pose Advice', path: '/pose-advice' },
    { number: 5, title: 'Pose Advice Result', path: '/pose-advice/result' }
  ];

  return (
    <Card className="mb-6">
      <CardContent className="pt-6">
        <div className="flex items-center justify-between">
          {steps.map((step, index) => (
            <div key={step.number} className="flex items-center">
              <Link href={step.path}>
                <div className={`w-8 h-8 rounded-full flex items-center justify-center font-bold text-sm cursor-pointer transition-colors hover:scale-105 ${
                  currentStep === step.number
                    ? 'bg-blue-500 text-white'
                    : currentStep > step.number
                    ? 'bg-green-500 text-white hover:bg-green-600'
                    : 'bg-gray-200 text-gray-600 hover:bg-gray-300'
                }`}>
                  {currentStep > step.number ? '✓' : step.number}
                </div>
              </Link>
              <Link href={step.path}>
                <span className={`ml-2 text-sm font-medium cursor-pointer transition-colors ${
                  currentStep >= step.number ? 'text-gray-900 hover:text-blue-600' : 'text-gray-500 hover:text-gray-700'
                }`}>
                  {step.title}
                </span>
              </Link>
              {index < steps.length - 1 && (
                <div className={`w-12 h-0.5 mx-4 ${
                  currentStep > step.number ? 'bg-green-500' : 'bg-gray-200'
                }`} />
              )}
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}
