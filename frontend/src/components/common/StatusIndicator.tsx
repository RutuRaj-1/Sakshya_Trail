import React from 'react';
import { cn } from '@/lib/utils';

export interface StatusIndicatorProps {
  status: 'online' | 'offline' | 'degraded' | 'pending';
  label?: string;
  className?: string;
}

export const StatusIndicator: React.FC<StatusIndicatorProps> = ({
  status,
  label,
  className,
}) => {
  const dotStyles = {
    online: 'bg-emerald-500 shadow-[0_0_8px_rgba(16,185,129,0.5)]',
    offline: 'bg-rose-500 shadow-[0_0_8px_rgba(244,63,94,0.5)]',
    degraded: 'bg-amber-500 shadow-[0_0_8px_rgba(245,158,11,0.5)]',
    pending: 'bg-blue-400 animate-pulse',
  };

  return (
    <div className={cn('inline-flex items-center gap-2 text-xs font-medium', className)}>
      <span className={cn('w-2 h-2 rounded-full', dotStyles[status])} />
      {label && <span className="text-slate-600 font-mono text-[11px]">{label}</span>}
    </div>
  );
};
