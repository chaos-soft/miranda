'use strict'
/* global Global, Mustache, XMLHttpRequest */

class Chat {
  constructor () {
    this.icons = { t: 't.ico', g: 'g.png', s: 's.ico', y: 'y.png' }
    this.isClean = false
    this.isScroll = true
    this.main = document.getElementsByClassName('main')[0]
    this.messages = document.getElementById('messages').innerHTML
    this.offset = 0
    this.systemIds = ['p', 'e', 'm', 'js']
  }

  clean () {
    this.isClean = false
    this.main.querySelectorAll(':scope > div').forEach((div) => div.remove())
  }

  core (data) {
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

  emptyData () {
  }

  preLoop () {
  }

  postLoop () {
  }

  processMessage (message) {
    message.classes = [message.id]
    if (message.id === 'js' && message.text === 'clean_chat') {
      this.isClean = true
    } else if (message.id in this.icons) {
      message.icon = this.icons[message.id]
      new Message(message).replace()
    }
    message.isSystem = () => {
      if (this.systemIds.indexOf(message.id) !== -1) {
        return true
      }
    }
    message.isNormal = () => {
      if (message.id in this.icons) {
        return true
      }
    }
    message.getClasses = () => message.classes.join(' ')
  }

  render (data) {
    this.main.insertAdjacentHTML('beforeend', Mustache.render(this.messages, data))
  }

  scroll () {
    if (this.isScroll) {
      window.scroll(0, this.main.scrollHeight)
    }
  }
}

class Message {
  constructor (message) {
    this.message = message
    this.replacements = 'replacements' in message ? message.replacements : []
    this.reSmile = /:\w+:/gi
  }

  prepareG () {
    const m = this.message.text.match(this.reSmile)
    if (m) {
      m.forEach((replacement) => {
        const smileName = replacement.slice(1, -1)
        let isFound = false
        Global.Smiles.some((smile) => {
          if (smile.name === smileName) {
            this.replacements.push([
              replacement,
              smile.animated ? smile.img_gif : smile.img_big
            ])
            isFound = true
            return true
          }
        })
        if (!isFound) {
          this.message.premiums.some((id) => {
            if (id in Global.Channel_Smiles) {
              Global.Channel_Smiles[id].some((smile) => {
                if (smile.name === smileName) {
                  this.replacements.push([
                    replacement,
                    smile.animated ? smile.img_gif : smile.img_big
                  ])
                  isFound = true
                  return true
                }
              })
              if (isFound) {
                return true
              }
            }
          })
        }
      })
    }
  }

  prepareS () {
    const m = this.message.text.match(this.reSmile)
    if (m) {
      m.forEach((replacement) => {
        const smileName = replacement.slice(1, -1)
        this.replacements.push([
          replacement,
          `https://sc2tv.ru/images/smiles/${smileName}.png`
        ])
      })
    }
  }

  prepareT () {
    for (const r of this.replacements) {
      if (r.length === 2) {
        r[1] = `https://static-cdn.jtvnw.net/emoticons/v1/${r[1]}/1.0`
      }
    }
  }

  replace_ () {
    let img
    let search
    this.replacements.forEach((replacement) => {
      if (replacement.length === 2) {
        img = `<img src="${replacement[1]}">`
        search = replacement[0]
      } else {
        img = `<img src="${replacement}">`
        search = replacement
      }
      this.message.text = this.message.text.replaceAll(search, img)
    })
  }

  replace () {
    if (this.message.id === 'g') {
      this.prepareG()
    } else if (this.message.id === 's') {
      this.prepareS()
    } else if (this.message.id === 't') {
      this.prepareT()
    }
    this.replace_()
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
