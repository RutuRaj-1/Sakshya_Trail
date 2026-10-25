import React from 'react';
import { cn } from '@/lib/utils';

export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'outline' | 'ghost' | 'danger';
  size?: 'sm' | 'md' | 'lg';
}

export const Button: React.FC<ButtonProps> = ({
  children,
  className,
  variant = 'primary',
  size = 'md',
  ...props
}) => {
  const baseStyles =
    'inline-flex items-center justify-center font-medium rounded-[8px] transition-colors focus:outline-none focus:ring-2 focus:ring-[#145DA0] focus:ring-offset-2 disabled:opacity-50 disabled:pointer-events-none cursor-pointer';

  const sizeStyles = {
    sm: 'text-xs px-2.5 py-1.5 gap-1.5',
    md: 'text-sm px-3.5 py-2 gap-2',
    lg: 'text-base px-5 py-2.5 gap-2.5',
  };

  const variantStyles = {
    primary:
      'bg-[#123B5D] text-white hover:bg-[#0D2538] focus:ring-[#145DA0] shadow-xs active:bg-[#071724]',
    secondary:
      'bg-white text-[#253746] border border-[#8799A9] hover:bg-[#EDF1F3] hover:text-[#0D2538] focus:ring-[#145DA0] shadow-2xs',
    outline:
      'border border-[#8799A9] bg-white text-[#253746] hover:bg-[#EDF1F3] hover:border-[#253746] focus:ring-[#145DA0]',
    ghost:
      'bg-transparent text-[#253746] hover:bg-[#EDF1F3] hover:text-[#0D2538]',
    danger:
      'bg-[#B42318] text-white hover:bg-[#8E1B13] focus:ring-[#B42318] shadow-xs',
  };

  return (
    <button
      className={cn(baseStyles, sizeStyles[size], variantStyles[variant], className)}
      {...props}
    >
      {children}
    </button>
  );
};

