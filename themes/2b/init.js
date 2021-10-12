'use strict'
/* global Chat, get */

class TwoBChat extends Chat {
  constructor () {
    super()
    this.offset = -10
  }

  emptyData () {
    this.removeMessages()
  }

  preLoop () {
    this.removeMessages()
  }

  postLoop () {
    setTimeout(() => {
      for (const div of this.main_.querySelectorAll(':scope > .o0')) {
        div.classList.remove('o0')
      }
    }, 100)
  }

  removeMessages () {
    for (const div of this.main_.querySelectorAll(':scope > div')) {
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

function main () {
  chat = new TwoBChat()
  setInterval(() => {
    get(
      `http://localhost:55555/messages?offset=${chat.offset}`,
      (data) => chat.main(data),
      () => chat.emptyData())
  }, 5 * 1000)
}

document.addEventListener('DOMContentLoaded', () => main())
