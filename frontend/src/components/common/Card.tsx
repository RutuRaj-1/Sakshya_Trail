import React from 'react';
import { cn } from '@/lib/utils';

export interface CardProps extends React.HTMLAttributes<HTMLDivElement> {
  hoverEffect?: boolean;
}

export const Card: React.FC<CardProps> = ({
  children,
  className,
  hoverEffect = false,
  ...props
}) => {
  return (
    <div
      className={cn(
        'bg-white rounded-xl border border-slate-200/80 shadow-sm shadow-slate-100 p-5 transition-all',
        hoverEffect && 'hover:border-sentinel-300 hover:shadow-md hover:shadow-slate-200/50',
        className
      )}
      {...props}
    >
      {children}
    </div>
  );
};
