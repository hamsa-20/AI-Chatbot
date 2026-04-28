import type { Metadata } from 'next';
import './globals.css';

export const metadata: Metadata = {
  title: 'Zoho Projects AI',
  description: 'AI-powered assistant for Zoho Projects',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className="h-full bg-[#0f1117] text-slate-200 antialiased">
        {children}
      </body>
    </html>
  );
}