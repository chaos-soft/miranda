'use strict'
/* global Mustache, XMLHttpRequest */

class Chat {
  constructor () {
    this.isClean = false
    this.isScroll = true
    this.main_ = document.getElementsByClassName('main')[0]
    this.messages = document.getElementById('messages').innerHTML
    this.offset = 0
  }

  clean () {
    this.isClean = false
    this.main_.querySelectorAll(':scope > div').forEach((div) => div.remove())
  }

  emptyData () {
  }

  main (data) {
    this.offset = data.total
    if (!data.messages.length) {
      this.emptyData()
      return
    }
    this.preLoop()
    data.messages.forEach((message) => this.processMessage(message))
    if (this.isClean) {
      this.clean()
    }
    this.render(data)
    this.postLoop()
  }

  postLoop () {
  }

  preLoop () {
  }

  processMessage (message) {
    if (message === 'clean_chat') {
      this.isClean = true
    }
  }

  render (data) {
    this.main_.insertAdjacentHTML('beforeend', Mustache.render(this.messages, data))
  }

  scroll () {
    if (this.isScroll) {
      const main = this.main_.offsetTop + this.main_.scrollHeight
      const window_ = window.innerHeight + window.scrollY
      if (main !== window_) {
        window.scroll(0, main)
      }
    }
  }
}

function get (url, callbackSuccess, callbackError) {
  const xhr = new XMLHttpRequest()
  xhr.addEventListener('load', () => {
    if (xhr.status === 200) {
      callbackSuccess(JSON.parse(xhr.responseText))
    }
  })
  xhr.addEventListener('error', () => {
    if (callbackError) {
      callbackError()
    }
  })
  xhr.open('GET', url, true)
  xhr.setRequestHeader('X-Requested-With', 'XMLHttpRequest')
  xhr.send()
}
