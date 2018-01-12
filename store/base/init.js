var icons = {t: 't.ico', g: 'g.png', s: 's.ico', y: 'y.png'}
var names
var main

var messagePattern = `<img src="/store/icons/{{ icon }}" alt="">
<span>{{ name }}</span>: {{ text }}`

var tts = []
tts.isBusy = false
tts.worker = function () {
  if (! tts.isBusy) {
    var message = tts.shift()

    if (message) {
      tts.isBusy = true
      tts.y.speak(message)
    }
  }
}

var core = function (data) {
  if (! data.length) {
    return
  }

  main.offset += data.length
  main.isScroll = false

  data.forEach(function (item) {
    var div

    if ('replacements' in item) {
      for (var k in item['replacements']) {
        var img = '<img src="' + item['replacements'][k] + '" alt="">'
        var r = RegExp(k, 'g')
        item['text'] = item['text'].replace(r, img)
      }
    }

    if (item['id'] in icons) {
      div = document.createElement('div')
      div.classList.add(item['id'])
      div.innerHTML = messagePattern
        .replace('{{ icon }}', icons[item['id']])
        .replace('{{ name }}', item['name'])
        .replace('{{ text }}', item['text'])
    } else if (item['id'] === 'js') {
      try {
        eval(item['command'])
      } catch (e) {
        console.log(e)
      }
    } else {
      div = document.createElement('div')
      div.classList.add('m')
      div.textContent = 'Miranda: ' + item['text']
    }

    if (div) {
      var divStr = div.textContent

      names.forEach(function (name) {
        if (divStr.search(name) !== -1) {
          div.classList.add('m')
        }
      })

      main.appendChild(div)
      main.isScroll = true
    }
  })

  if (main.isScroll) {
    scroll()
  }
}

var error = function () {
  if (main.offset) {
    var div = document.createElement('div')
    div.classList.add('m')
    div.textContent = 'Miranda: потеряно соединение.'

    main.appendChild(div)
    scroll()
  }

  main.offset = 0
}

var scroll = function () {
  setTimeout(function () {
    window.scrollTo(0, main.scrollHeight)
  }, 200)
}

document.addEventListener('DOMContentLoaded', function () {
  main = document.getElementById('main')
  main.offset = 0

  tts.y = new window.ya.speechkit.Tts({
    speaker: 'omazh',
    stopCallback: function () {
        tts.isBusy = false
    }
  })

  setInterval(function () {
    window.get('/comments?offset=' + main.offset, core, error)
  }, 5 * 1000)

  setInterval(tts.worker, 100)
})
