import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import { BrowserRouter } from 'react-router-dom';
import { Badge } from '@/components/common/Badge';
import { Button } from '@/components/common/Button';
import { StatusIndicator } from '@/components/common/StatusIndicator';
import { LoginPage } from '@/app/routes/LoginPage';
import { AuthProvider } from '@/features/auth/AuthContext';

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

describe('Authentication Views', () => {
  it('renders LoginPage with official branding and form inputs', () => {
    render(
      <AuthProvider>
        <BrowserRouter>
          <LoginPage />
        </BrowserRouter>
      </AuthProvider>
    );

    expect(screen.getByRole('heading', { name: /Welcome Back/i })).toBeInTheDocument();
    expect(screen.getByLabelText(/Official Email Address/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/^Password$/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Sign In to SakshyaTrail/i })).toBeInTheDocument();
  });
});
