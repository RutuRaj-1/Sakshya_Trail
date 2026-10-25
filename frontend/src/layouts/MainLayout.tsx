import React from 'react';
import { Outlet } from 'react-router-dom';
import { Header } from '@/components/navigation/Header';
import { Sidebar } from '@/components/navigation/Sidebar';

export const MainLayout: React.FC = () => {
  return (
    <div className="flex h-screen bg-[#F5F4EF] text-[#253746] overflow-hidden font-sans antialiased">
      <Sidebar />
      <div className="flex-1 flex flex-col min-w-0 overflow-hidden bg-[#F5F4EF]">
        <Header />
        <main className="flex-1 overflow-y-auto px-4 py-5 sm:px-6 sm:py-6 lg:px-8 lg:py-8">
          <div className="max-w-7xl mx-auto">
            <Outlet />
          </div>
        </main>
      </div>
    </div>
  );
};

