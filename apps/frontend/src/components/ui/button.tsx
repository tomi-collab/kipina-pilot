import * as React from 'react'
import { cva, type VariantProps } from 'class-variance-authority'
import { cn } from '@/lib/utils'

const buttonVariants = cva(
  'inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-[var(--radius)] font-semibold transition-colors disabled:pointer-events-none disabled:opacity-50 select-none',
  {
    variants: {
      variant: {
        primary:
          'bg-[var(--color-accent)] text-[var(--color-accent-fg)] hover:bg-[var(--color-accent-hover)]',
        secondary:
          'bg-[var(--color-surface-elevated)] text-[var(--color-text)] hover:bg-[var(--color-border)]',
        ghost:
          'bg-transparent text-[var(--color-text)] hover:bg-[var(--color-surface)]',
      },
      size: {
        // Min-korkeus 48px = WCAG 2.5.5 AAA
        md: 'min-h-12 px-5 text-base',
        lg: 'min-h-14 px-7 text-lg',
        xl: 'min-h-16 px-8 text-xl',
      },
    },
    defaultVariants: {
      variant: 'primary',
      size: 'lg',
    },
  }
)

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {}

export const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant, size, ...props }, ref) => {
    return (
      <button
        ref={ref}
        className={cn(buttonVariants({ variant, size }), className)}
        {...props}
      />
    )
  }
)
Button.displayName = 'Button'
