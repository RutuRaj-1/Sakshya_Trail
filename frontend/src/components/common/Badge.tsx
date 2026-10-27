import React from 'react';
import { cn } from '@/lib/utils';

export interface BadgeProps extends React.HTMLAttributes<HTMLSpanElement> {
  variant?: 'default' | 'success' | 'warning' | 'danger' | 'info' | 'outline' | 'purple' | 'simulated' | 'teal' | 'gold';
}

export const Badge: React.FC<BadgeProps> = ({
  children,
  className,
  variant = 'default',
  ...props
}) => {
  const variantStyles = {
    default: 'bg-[#EDF1F3] text-[#253746] border-[#C9D3DB]',
    success: 'bg-[#E7F3EC] text-[#18794E] border-[#B4DFC9]',
    warning: 'bg-[#FEF7E8] text-[#8A5A00] border-[#F8DEAE]',
    danger: 'bg-[#FDF2F1] text-[#B42318] border-[#FECDCA]',
    info: 'bg-[#EEF6FA] text-[#245B7A] border-[#C4DEED]',
    simulated: 'bg-[#FFF3D6] text-[#7A4B00] border-[#E5C278] font-bold tracking-wider',
    teal: 'bg-[#E6F4F2] text-[#0F766E] border-[#99D5CE]',
    gold: 'bg-[#FAF4E8] text-[#8A5A00] border-[#EAD9B4]',
    purple: 'bg-[#F3EEF9] text-[#5B3A82] border-[#D4C4E8]',
    outline: 'border-[#8799A9] text-[#253746] bg-white',
  };

  return (
    <span
      className={cn(
        'inline-flex items-center px-2 py-0.5 rounded-none text-xs font-medium border tracking-wide transition-colors',
        variantStyles[variant],
        className
      )}
      {...props}
    >
      {children}
    </span>
  );
};

