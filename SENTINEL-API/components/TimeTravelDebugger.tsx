'use client';

import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { CheckCircle2, Clock, PlayCircle, Loader2 } from 'lucide-react';

interface HistoryStep {
    step: number;
    action: string;
    timestamp: string;
    details: string;
}

interface TimeTravelDebuggerProps {
    history: HistoryStep[];
}

export function TimeTravelDebugger({ history }: TimeTravelDebuggerProps) {
    const [currentStep, setCurrentStep] = useState(0);
    const [isPlaying, setIsPlaying] = useState(false);

    // Playback effect
    useEffect(() => {
        let timer: NodeJS.Timeout;
        if (isPlaying && currentStep < history.length) {
            timer = setTimeout(() => {
                setCurrentStep((prev) => prev + 1);
            }, 1200); // 1.2 second per step
        } else if (currentStep >= history.length) {
            setIsPlaying(false);
        }
        return () => clearTimeout(timer);
    }, [isPlaying, currentStep, history.length]);

    const handlePlay = () => {
        if (currentStep >= history.length) setCurrentStep(0);
        setIsPlaying(true);
    };

    if (!history || history.length === 0) return null;

    return (
        <Card className="w-full mt-6 border-slate-800 bg-slate-950 text-slate-100">
            <CardHeader className="flex flex-row items-center justify-between pb-2">
                <div>
                    <CardTitle className="text-xl font-bold flex items-center gap-2 text-blue-400">
                        <Clock className="h-5 w-5" />
                        AI Reasoning Playback
                    </CardTitle>
                    <CardDescription className="text-slate-400">
                        Time-Travel Debugger: Watch the LangGraph processing steps.
                    </CardDescription>
                </div>
                <button
                    onClick={handlePlay}
                    disabled={isPlaying}
                    className="flex items-center gap-2 bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-md transition-colors disabled:opacity-50"
                >
                    {isPlaying ? <Loader2 className="h-4 w-4 animate-spin" /> : <PlayCircle className="h-4 w-4" />}
                    {isPlaying ? 'Playing...' : 'Replay'}
                </button>
            </CardHeader>
            <CardContent>
                <div className="relative border-l border-slate-800 ml-4 mt-4 space-y-6 pb-4">
                    {history.map((step, idx) => {
                        const isVisible = idx <= currentStep || currentStep >= history.length - 1;
                        const isCurrent = idx === currentStep && isPlaying;

                        return (
                            <div
                                key={idx}
                                className={`relative pl-8 transition-all duration-500 ease-in-out ${isVisible ? 'opacity-100 transform translate-y-0' : 'opacity-0 transform translate-y-4 hidden'
                                    }`}
                            >
                                {/* Timeline dot */}
                                <div className={`absolute -left-[9px] top-1 h-4 w-4 rounded-full border-2 bg-slate-950 ${isCurrent ? 'border-blue-500 animate-pulse' : 'border-green-500'
                                    }`}>
                                    {!isCurrent && <CheckCircle2 className="h-3 w-3 text-green-500 absolute -top-[1.5px] -left-[1.5px]" />}
                                    {isCurrent && <div className="h-1.5 w-1.5 bg-blue-500 rounded-full absolute top-[3px] left-[3px]" />}
                                </div>

                                <div className={`bg-slate-900 border ${isCurrent ? 'border-blue-500/50 shadow-[0_0_15px_rgba(59,130,246,0.2)]' : 'border-slate-800'} rounded-lg p-4`}>
                                    <div className="flex justify-between items-start mb-1">
                                        <h4 className="font-semibold text-sm sm:text-base text-slate-200">
                                            Step {step.step}: {step.action}
                                        </h4>
                                        <span className="text-xs text-slate-500 font-mono">
                                            {new Date(step.timestamp).toLocaleTimeString([], { hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit' })}
                                        </span>
                                    </div>
                                    <p className="text-sm text-slate-400 mt-2">{step.details}</p>
                                </div>
                            </div>
                        );
                    })}
                </div>
            </CardContent>
        </Card>
    );
}
