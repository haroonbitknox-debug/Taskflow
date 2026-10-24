import assert from 'node:assert/strict'
import test from 'node:test'

import api, { authApi } from './api.js'

function response(config, data = {}) {
  return {
    config,
    data,
    headers: {},
    status: 200,
    statusText: 'OK',
  }
}

test('uses and refreshes CSRF tokens across registration and login', async () => {
  const previousAdapter = api.defaults.adapter
  let cookieToken = null
  let csrfRequests = 0

  api.defaults.adapter = async (config) => {
    assert.equal(config.withCredentials, true)
    if (config.url === '/auth/csrf') {
      cookieToken = `test-token-${++csrfRequests}`
      const csrfResponse = response(config, { csrf_token: cookieToken })
      assert.equal(csrfResponse.data.csrf_token, cookieToken)
      return csrfResponse
    }

    assert.equal(config.headers.get('X-CSRF-Token'), cookieToken)
    if (['/auth/login', '/auth/register'].includes(config.url)) {
      cookieToken = `rotated-${config.url.slice('/auth/'.length)}-token`
    }
    return response(config)
  }

  try {
    await authApi.register({
      full_name: 'Test User',
      email: 'test@example.test',
      password: 'test-password',
    })
    await api.post('/tasks', {})
    await authApi.login({ email: 'test@example.test', password: 'test-password' })
    await api.post('/tasks', {})

    assert.equal(csrfRequests, 3)
  } finally {
    api.defaults.adapter = previousAdapter
  }
})
