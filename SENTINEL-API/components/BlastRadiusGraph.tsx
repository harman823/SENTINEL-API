'use client';

import React from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Network, AlertCircle, Maximize2 } from 'lucide-react';

interface BlastRadiusData {
    blast_radius_by_schema?: Record<string, string[]>;
    nodes?: Array<{ id: string; label: string; type: string }>;
    edges?: Array<{ source: string; target: string; type: string }>;
}

interface BlastRadiusGraphProps {
    data: BlastRadiusData | null | undefined;
}

export function BlastRadiusGraph({ data }: BlastRadiusGraphProps) {
    if (!data || !data.blast_radius_by_schema || Object.keys(data.blast_radius_by_schema).length === 0) {
        return null;
    }

    const schemas = Object.entries(data.blast_radius_by_schema);

    return (
        <Card className="w-full mt-6 border-indigo-900/50 bg-slate-950 text-slate-100 overflow-hidden relative">
            <div className="absolute top-0 right-0 w-64 h-64 bg-indigo-600/10 rounded-full blur-3xl -mr-20 -mt-20 pointer-events-none" />
            <CardHeader className="pb-2 relative z-10">
                <div className="flex items-center gap-2 text-indigo-400">
                    <Network className="h-5 w-5" />
                    <CardTitle className="text-xl font-bold">API Blast Radius</CardTitle>
                </div>
                <CardDescription className="text-slate-400">
                    Dependency Graph: Shows which endpoints are impacted when a core schema is changed.
                </CardDescription>
            </CardHeader>
            <CardContent className="relative z-10">
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 mt-4">
                    {schemas.map(([schema, endpoints]) => (
                        <div key={schema} className="bg-slate-900 border border-slate-800 rounded-lg p-4 flex flex-col hover:border-indigo-500/50 transition-colors">
                            <div className="flex items-center gap-2 mb-3 pb-2 border-b border-slate-800">
                                <div className="h-2 w-2 rounded-full bg-indigo-500" />
                                <h4 className="font-semibold text-slate-200 truncate" title={schema}>{schema}</h4>
                            </div>

                            <div className="flex-1">
                                <p className="text-xs text-slate-500 mb-2 font-medium uppercase tracking-wider">Impacted Endpoints ({endpoints.length})</p>
                                {endpoints.length === 0 ? (
                                    <p className="text-sm text-slate-600 italic">No direct dependencies</p>
                                ) : (
                                    <ul className="space-y-1.5 max-h-32 overflow-y-auto pr-2 custom-scrollbar">
                                        {endpoints.map((ep, idx) => {
                                            const method = ep.split(' ')[0] || '';
                                            let methodColor = 'text-slate-400';
                                            if (method === 'GET') methodColor = 'text-green-400';
                                            if (method === 'POST') methodColor = 'text-blue-400';
                                            if (method === 'DELETE') methodColor = 'text-red-400';
                                            if (method === 'PUT' || method === 'PATCH') methodColor = 'text-yellow-400';

                                            return (
                                                <li key={idx} className="text-xs flex items-start gap-2 bg-slate-950 rounded p-1.5 border border-slate-800/50">
                                                    <span className={`${methodColor} font-bold w-10 shrink-0`}>{method}</span>
                                                    <span className="text-slate-300 font-mono truncate">{ep.substring(method.length).trim()}</span>
                                                </li>
                                            );
                                        })}
                                    </ul>
                                )}
                            </div>

                            {endpoints.length > 3 && (
                                <div className="mt-3 pt-2 border-t border-slate-800/50 flex items-center gap-1 text-xs text-amber-500/80">
                                    <AlertCircle className="h-3 w-3" />
                                    <span>High impact on change</span>
                                </div>
                            )}
                        </div>
                    ))}
                </div>
            </CardContent>
        </Card>
    );
}
