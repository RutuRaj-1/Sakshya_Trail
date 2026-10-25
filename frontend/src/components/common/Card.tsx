import React from 'react';
import { cn } from '@/lib/utils';

export interface CardProps extends React.HTMLAttributes<HTMLDivElement> {
  hoverEffect?: boolean;
  emphasis?: boolean;
}

export const Card: React.FC<CardProps> = ({
  children,
  className,
  hoverEffect = false,
  emphasis = false,
  ...props
}) => {
  return (
    <div
      className={cn(
        'bg-white rounded-[10px] border border-[#C9D3DB] p-5 shadow-[0_1px_3px_rgba(13,37,56,0.04)] transition-all',
        emphasis && 'border-2 border-[#123B5D]',
        hoverEffect && 'hover:border-[#8799A9] hover:shadow-[0_4px_12px_rgba(13,37,56,0.06)]',
        className
      )}
      {...props}
    >
      {children}
    </div>
  );
};

