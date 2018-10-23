'use strict'
/* global XMLHttpRequest, scrollTo, Global */

window.get = function (url, callbackSuccess, callbackError) {
  var xhr = new XMLHttpRequest()
  xhr.addEventListener('load', function () {
    if (xhr.status === 200) {
      callbackSuccess(JSON.parse(this.responseText))
    }
  })
  xhr.addEventListener('error', function () {
    if (callbackError) {
      callbackError()
    }
  })
  xhr.open('GET', url, true)
  xhr.setRequestHeader('X-Requested-With', 'XMLHttpRequest')
  xhr.send()
}

window.Chat = class {
  constructor (element) {
    this.element = element
    this.offset = 0
    this.includeIds = ['p', 'e', 'm', 'tts', 'js']
    this.icons = { t: 't.ico', g: 'g.png', s: 's.ico', y: 'y.png' }
    this.m = '<img src="/store/icons/{{ icon }}"> <span>{{ name }}</span>: {{ text }}'
  }

  preLoop () {
  }

  postLoop () {
  }

  preCreateDiv (message) {
  }

  postCreateDiv (div, message) {
  }

  emptyData () {
  }

  core (data) {
    this.offset = data['total']
    if (!data['messages'].length) {
      this.emptyData()
      return
    }
    this.preLoop()
    var thisCache = this
    data['messages'].forEach(function (message) {
      thisCache.preCreateDiv(message)
      var div
      if (message['id'] in thisCache.icons) {
        div = document.createElement('div')
        div.classList.add(message['id'])
        div.innerHTML = thisCache.m
          .replace('{{ icon }}', thisCache.icons[message['id']])
          .replace('{{ name }}', message['name'])
          .replace('{{ text }}', message['text'])
      } else if (thisCache.includeIds.indexOf(message['id']) !== -1) {
        div = document.createElement('div')
        div.classList.add('m')
        div.innerHTML = `Miranda: ${message['text']}`
      }
      if (div) {
        thisCache.postCreateDiv(div, message)
        thisCache.element.appendChild(div)
      }
    })
    this.postLoop()
  }

  scroll (timeout = 200) {
    var thisCache = this
    setTimeout(function () {
      scrollTo(0, thisCache.element.scrollHeight)
    }, timeout)
  }
}

window.Message = class {
  constructor (message) {
    this.message = message
    this.replacements = 'replacements' in message ? message['replacements'] : []
    this.reSmile = /:\w+:/gi
  }

  prepareG () {
    var m = this.message['text'].match(this.reSmile)
    if (m) {
      var thisCache = this
      m.forEach(function (replacement) {
        var smileName = replacement.slice(1, -1)
        var isFound = false
        Global['Smiles'].some(function (smile) {
          if (smile['name'] === smileName) {
            thisCache.replacements.push([
              replacement,
              smile['animated'] ? smile['img_gif'] : smile['img_big']
            ])
            isFound = true
            return true
          }
        })
        if (!isFound) {
          thisCache.message['premiums'].some(function (id) {
            if (id in Global['Channel_Smiles']) {
              Global['Channel_Smiles'][id].some(function (smile) {
                if (smile['name'] === smileName) {
                  thisCache.replacements.push([
                    replacement,
                    smile['animated'] ? smile['img_gif'] : smile['img_big']
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
    var m = this.message['text'].match(this.reSmile)
    if (m) {
      var thisCache = this
      m.forEach(function (replacement) {
        var smileName = replacement.slice(1, -1)
        thisCache.replacements.push([
          replacement,
          `https://peka2.tv/images/smiles/${smileName}.png`
        ])
      })
    }
  }

  prepareT () {
    var thisCache = this
    this.message['emotes'].split('/').forEach(function (emote) {
      var idIndexes = emote.split(':')
      idIndexes[1].split(',').forEach(function (i) {
        i = i.split('-')
        thisCache.replacements.push([
          thisCache.message['text'].substring(parseInt(i[0]), parseInt(i[1]) + 1),
          `https://static-cdn.jtvnw.net/emoticons/v1/${idIndexes[0]}/1.0`
        ])
      })
    })
  }

  replace_ () {
    var search
    var img
    var thisCache = this
    this.replacements.reverse().forEach(function (replacement) {
      if (replacement.length === 2) {
        search = replacement[0]
        img = `<img src="${replacement[1]}">`
      } else {
        search = replacement
        img = `<img src="${replacement}">`
      }
      thisCache.message['text'] = thisCache.message['text'].replace(search, img)
    })
  }

  replace () {
    if (this.message['id'] === 'g') {
      this.prepareG()
    } else if (this.message['id'] === 's') {
      this.prepareS()
    } else if (this.message['id'] === 't' && this.message['emotes']) {
      this.prepareT()
    }
    this.replace_()
  }
}
