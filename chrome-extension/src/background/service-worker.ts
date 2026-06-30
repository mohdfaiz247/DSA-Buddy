import { API_BASE_URL } from '../lib/api';

console.log('DSA Buddy Service Worker Initialized');

chrome.runtime.onInstalled.addListener(() => {
  console.log('Extension installed');
});

// Intercept messages from popup/content scripts to handle auth securely
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request.type === 'LOGIN') {
    handleLogin(request.payload).then(sendResponse);
    return true; // Keep the message channel open for async response
  }
  if (request.type === 'REGISTER') {
    handleRegister(request.payload).then(sendResponse);
    return true;
  }
});

async function handleLogin(credentials: any) {
  try {
    const response = await fetch(`${API_BASE_URL}/api/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(credentials)
    });
    const data = await response.json();
    if (response.ok) {
      await chrome.storage.local.set({ token: data.access_token });
      return { success: true };
    }
    return { success: false, error: data.detail };
  } catch (error: any) {
    return { success: false, error: error.message };
  }
}

async function handleRegister(userData: any) {
  try {
    const response = await fetch(`${API_BASE_URL}/api/auth/register`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(userData)
    });
    const data = await response.json();
    if (response.ok) {
      return { success: true };
    }
    return { success: false, error: data.detail };
  } catch (error: any) {
    return { success: false, error: error.message };
  }
}
