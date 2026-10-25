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
    online: 'bg-[#18794E] shadow-[0_0_6px_rgba(24,121,78,0.4)]',
    offline: 'bg-[#B42318] shadow-[0_0_6px_rgba(180,35,24,0.4)]',
    degraded: 'bg-[#8A5A00] shadow-[0_0_6px_rgba(138,90,0,0.4)]',
    pending: 'bg-[#245B7A] animate-pulse',
  };

  return (
    <div className={cn('inline-flex items-center gap-2 text-xs font-medium', className)}>
      <span className={cn('w-2 h-2 rounded-full shrink-0', dotStyles[status])} />
      {label && <span className="text-[#253746] font-mono text-[11px]">{label}</span>}
    </div>
  );
};

