window.get = function (url, callbackSuccess, callbackError) {
  var xhr = new window.XMLHttpRequest()
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
