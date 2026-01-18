import { Elder, CallSession, VillageAction, DemoConfig } from '../types';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

class ApiClient {
  private baseUrl: string;

  constructor(baseUrl: string) {
    this.baseUrl = baseUrl;
  }

  private async request<T>(
    endpoint: string,
    options?: RequestInit
  ): Promise<T> {
    const url = `${this.baseUrl}${endpoint}`;
    console.log(`🔗 [API] Making ${options?.method || 'GET'} request to: ${url}`);

    try {
      const response = await fetch(url, {
        ...options,
        headers: {
          'Content-Type': 'application/json',
          ...options?.headers,
        },
      });

      console.log(`📡 [API] Response status: ${response.status} ${response.statusText}`);

      if (!response.ok) {
        const error = await response.text();
        console.error(`❌ [API] Error response:`, error);
        throw new Error(`API Error: ${response.status} - ${error}`);
      }

      const data = await response.json();
      console.log(`✅ [API] Response data:`, data);
      return data;
    } catch (error) {
      console.error('❌ [API] Request failed:', error);
      throw error;
    }
  }

  // Elder endpoints
  async getElder(elderId: string): Promise<Elder> {
    return this.request<Elder>(`/api/elder/${elderId}`);
  }

  async getElderHistory(elderId: string, limit: number = 10): Promise<CallSession[]> {
    return this.request<CallSession[]>(`/api/elder/${elderId}/history?limit=${limit}`);
  }

  // Call endpoints
  async startCall(elderId: string, phoneNumber?: string): Promise<CallSession> {
    console.log('🌐 [API] startCall() called');
    console.log('   - elderId:', elderId);
    console.log('   - phoneNumber:', phoneNumber);
    console.log('   - API endpoint:', `${this.baseUrl}/api/call/start`);

    const requestBody = {
      elder_id: elderId,
      phone_number: phoneNumber
    };
    console.log('   - Request body:', requestBody);

    return this.request<CallSession>('/api/call/start', {
      method: 'POST',
      body: JSON.stringify(requestBody),
    });
  }

  async endCall(callId: string): Promise<CallSession> {
    return this.request<CallSession>(`/api/call/${callId}/end`, {
      method: 'POST',
    });
  }

  async getCall(callId: string): Promise<CallSession> {
    return this.request<CallSession>(`/api/call/${callId}`);
  }

  async listCalls(elderId?: string, limit: number = 20): Promise<CallSession[]> {
    const params = new URLSearchParams();
    if (elderId) params.append('elder_id', elderId);
    params.append('limit', limit.toString());

    return this.request<CallSession[]>(`/api/calls?${params}`);
  }

  // Village endpoints
  async triggerVillageAction(action: VillageAction): Promise<VillageAction> {
    return this.request<VillageAction>('/api/village/trigger', {
      method: 'POST',
      body: JSON.stringify(action),
    });
  }

  async listVillageActions(callId?: string, status?: string): Promise<VillageAction[]> {
    const params = new URLSearchParams();
    if (callId) params.append('call_id', callId);
    if (status) params.append('status', status);

    return this.request<VillageAction[]>(`/api/village/actions?${params}`);
  }

  // Demo endpoints
  async resetDemo(): Promise<void> {
    return this.request<void>('/api/demo/reset', {
      method: 'POST',
    });
  }

  async simulateConcern(concernType: string, severity: string): Promise<void> {
    return this.request<void>('/api/demo/simulate-concern', {
      method: 'POST',
      body: JSON.stringify({ concern_type: concernType, severity }),
    });
  }
}

export const api = new ApiClient(API_BASE_URL);
