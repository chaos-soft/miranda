'use strict'
/* global Chat, get */

class TwoBChat extends Chat {
  constructor () {
    super()
    this.offset = -10
    this.systemIds = ['p', 'e']
  }

  emptyData () {
    this.removeMessages()
  }

  preLoop () {
    this.removeMessages()
  }

  postLoop () {
    setTimeout(() => {
      for (const div of this.main.querySelectorAll(':scope > .o0')) {
        div.classList.remove('o0')
      }
    }, 100)
  }

  removeMessages () {
    for (const div of this.main.querySelectorAll(':scope > div')) {
      if (div.classList.contains('remove')) {
        div.remove()
      } else {
        div.classList.add('remove')
        div.style.marginTop = `-${div.offsetHeight}px`
      }
    }
  }
}

let chat

function init () {
  chat = new TwoBChat()
  setInterval(() => {
    get(
      `/messages?offset=${chat.offset}`,
      (data) => chat.core(data))
  }, 5 * 1000)
}

document.addEventListener('DOMContentLoaded', () => init())
