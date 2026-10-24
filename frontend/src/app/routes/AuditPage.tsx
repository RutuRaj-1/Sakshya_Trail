import React, { useEffect, useState } from 'react';
import { apiClient } from '@/api/client';
import { Card } from '@/components/common/Card';
import { Badge } from '@/components/common/Badge';
import { formatDate } from '@/lib/utils';
import { History, Shield } from 'lucide-react';

interface AuditEvent {
  id: string;
  entity_type: string;
  entity_id: string;
  action: string;
  actor_email: string;
  actor_role: string;
  details?: string;
  ip_address?: string;
  created_at: string;
}

export const AuditPage: React.FC = () => {
  const [events, setEvents] = useState<AuditEvent[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    async function load() {
      setIsLoading(true);
      try {
        const data = await apiClient.get<AuditEvent[]>('/audit');
        setEvents(data);
      } catch {
        setEvents([]);
      } finally {
        setIsLoading(false);
      }
    }
    load();
  }, []);

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      <div>
        <h1 className="text-xl font-bold text-slate-900 tracking-tight flex items-center gap-2">
          <History className="w-5 h-5 text-sentinel-600" /> Tamper-Evident Audit History
        </h1>
        <p className="text-xs text-slate-500">
          Immutable regulatory event ledger tracking all transitions, verification changes, and release authorizations
        </p>
      </div>

      {isLoading ? (
        <div className="bg-white rounded-xl border border-slate-200 p-8 text-center text-slate-500">
          <div className="inline-block animate-spin rounded-full h-8 w-8 border-4 border-slate-200 border-t-sentinel-600 mb-3" />
          <p className="text-sm">Querying audit logs...</p>
        </div>
      ) : events.length === 0 ? (
        <Card className="p-12 text-center">
          <Shield className="w-12 h-12 text-slate-300 mx-auto mb-3" />
          <h3 className="text-base font-semibold text-slate-800">Audit Trail Clean & Active</h3>
          <p className="text-sm text-slate-500 max-w-md mx-auto mt-1">
            System audit logging is enabled and monitored. As actions such as FDR submission, scrutiny check, and renewal occur, immutable events are appended here.
          </p>
        </Card>
      ) : (
        <div className="bg-white rounded-xl border border-slate-200 overflow-hidden shadow-xs">
          <table className="w-full text-left text-sm text-slate-700">
            <thead className="bg-slate-50 border-b border-slate-200 text-xs uppercase font-semibold text-slate-500 tracking-wider">
              <tr>
                <th className="py-3 px-4">Timestamp</th>
                <th className="py-3 px-4">Target Entity</th>
                <th className="py-3 px-4">Action</th>
                <th className="py-3 px-4">Actor</th>
                <th className="py-3 px-4">Role</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 font-mono text-xs">
              {events.map((e) => (
                <tr key={e.id}>
                  <td className="py-3 px-4 text-slate-500">{formatDate(e.created_at)}</td>
                  <td className="py-3 px-4 text-slate-800">{e.entity_type}:{e.entity_id.slice(0, 8)}</td>
                  <td className="py-3 px-4 font-bold text-sentinel-700">{e.action}</td>
                  <td className="py-3 px-4 text-slate-600">{e.actor_email}</td>
                  <td className="py-3 px-4">
                    <Badge variant="outline">{e.actor_role}</Badge>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
};
