import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import { Badge } from '@/components/common/Badge';
import { Button } from '@/components/common/Button';
import { StatusIndicator } from '@/components/common/StatusIndicator';

describe('Common UI Components', () => {
  it('renders Badge with correct text and style', () => {
    render(<Badge variant="success">Active FDR</Badge>);
    expect(screen.getByText('Active FDR')).toBeInTheDocument();
  });

  it('renders Button with children', () => {
    render(<Button>Submit Record</Button>);
    expect(screen.getByRole('button', { name: /Submit Record/i })).toBeInTheDocument();
  });

  it('renders StatusIndicator with online state', () => {
    render(<StatusIndicator status="online" label="Database Connected" />);
    expect(screen.getByText('Database Connected')).toBeInTheDocument();
  });
});
