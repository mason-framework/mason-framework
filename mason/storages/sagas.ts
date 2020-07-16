import { v4 as uuid4 } from 'uuid'
import { eventChannel } from 'redux-saga'
import {
  all,
  delay,
  put,
  call,
  take,
  takeEvery,
  select,
} from 'redux-saga/effects'
import { CONFIG_CHANGED, INITIALIZED } from 'store/app/types'
import { PROFILE_ENABLED, Event, EnableProfileAction } from 'store/profile/types'
import { RUN_STARTED } from 'store/runs/types'
import { getConfig } from 'store/app/selectors'
import {
  addEvents,
  disableProfile,
  changeRequestTime,
  changeEnabled,
} from 'store/profile/actions'
import { getActive, getEnabled } from 'store/profile/selectors'

/* eslint-disable camelcase */
interface ServerEvent {
  occurred_at: number
  event_type: string
  uid?: string
}
/* eslint-enable camelcase */

function parseEvents(eventData: string): Array<Event> {
  const events = JSON.parse(eventData)
  return events.map((ev: ServerEvent) => ({
    eventType: ev.event_type,
    occurredAt: ev.occurred_at,
    nodeId: ev.uid,
    uid: uuid4(),
  }))
}

function createEventChannel(host: string) {
  const url = new URL(host)
  url.protocol = url.protocol === 'https:' ? 'wss:' : 'ws:'
  const sock = new WebSocket(`${url.toString()}streams/profile`)
  return eventChannel((emit) => {
    sock.onerror = () => emit(disableProfile())
    sock.onclose = () => emit(disableProfile())
    sock.onmessage = (message) => emit(addEvents(parseEvents(message.data)))
    return () => sock.close()
  })
}

function* initConnectionSaga(action: EnableProfileAction) {
  const { enabled } = action
  if (enabled) {
    const { apiHost } = yield select(getConfig)
    const channel = yield call(createEventChannel, apiHost)
    while (yield select(getEnabled)) {
      const channelAction = yield take(channel)
      yield put(channelAction)
    }
  }
}

function* resetConnectionSaga() {
  const enabled = yield select(getEnabled)
  if (enabled) {
    yield put(changeEnabled(false))
    yield put(changeEnabled(true))
  }
}

function* initProfileSaga() {
  const enabled = yield select(getEnabled)
  if (enabled) {
    yield initConnectionSaga(changeEnabled(true) as EnableProfileAction)
  }
}

function* startProfileSaga() {
  const start = Date.now()
  while (yield select(getActive)) {
    yield put(changeRequestTime((Date.now() - start) / 1000))
    yield delay(100)
  }
}

export function* profileSaga() {
  yield all([
    takeEvery(INITIALIZED, initProfileSaga),
    takeEvery(PROFILE_ENABLED, initConnectionSaga),
    takeEvery(CONFIG_CHANGED, resetConnectionSaga),
    takeEvery(RUN_STARTED, startProfileSaga),
  ])
}
