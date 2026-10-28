import { describe, it, expect, vi, beforeEach } from 'vitest';
import { apiClient } from '@/api/client';
import { documentsApi } from '@/api/endpoints';

describe('ApiClient FormData & Document Upload Boundary', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it('passes FormData directly without JSON stringifying and removes manual Content-Type', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      text: async () => JSON.stringify({ success: true, document_id: 'doc-123' }),
    });
    vi.stubGlobal('fetch', fetchMock);

    const formData = new FormData();
    formData.append('title', 'Test FDR');
    const fakeFile = new Blob(['%PDF-1.4 test content'], { type: 'application/pdf' });
    formData.append('file', fakeFile, 'test.pdf');

    const result = await apiClient.post<{ success: boolean; document_id: string }>(
      '/test-upload',
      formData,
      { headers: { 'Content-Type': 'multipart/form-data', 'X-Custom-Header': 'custom-val' } }
    );

    expect(result.success).toBe(true);
    expect(fetchMock).toHaveBeenCalledTimes(1);

    const [url, requestOptions] = fetchMock.mock.calls[0];
    expect(url).toContain('/test-upload');
    // Body must be the raw FormData instance, not "{}"
    expect(requestOptions.body).toBe(formData);

    // Headers must NOT have Content-Type so browser sets boundary
    expect(requestOptions.headers['Content-Type']).toBeUndefined();
    expect(requestOptions.headers['content-type']).toBeUndefined();
    expect(requestOptions.headers['X-Custom-Header']).toBe('custom-val');
  });

  it('documentsApi.upload sends FormData without manual Content-Type header', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      text: async () => JSON.stringify({ success: true, document_id: 'doc-999' }),
    });
    vi.stubGlobal('fetch', fetchMock);

    const formData = new FormData();
    formData.append('category', 'FDR_CERTIFICATE');

    await documentsApi.upload('inst-123', formData);

    expect(fetchMock).toHaveBeenCalledTimes(1);
    const [url, requestOptions] = fetchMock.mock.calls[0];
    expect(url).toContain('/instruments/inst-123/documents');
    expect(requestOptions.body).toBe(formData);
    expect(requestOptions.headers['Content-Type']).toBeUndefined();
  });
});
