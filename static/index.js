/*
Base JS
 */

console.log('base JS loaded')

export function makePrettyTime (inputSeconds) {
  /**
  * [Pretty format seconds into HH:MM:SS]
  * @param  {[int]} inputSeconds [input seconds]
  */

  var secNum = parseInt(inputSeconds, 10)
  var hours = Math.floor(secNum / 3600)
  var minutes = Math.floor((secNum - (hours * 3600)) / 60)
  var seconds = secNum - (hours * 3600) - (minutes * 60)

  if (hours < 10) { hours = '0' + hours }
  if (minutes < 10) { minutes = '0' + minutes }
  if (seconds < 10) { seconds = '0' + seconds }
  return hours + ':' + minutes + ':' + seconds
}
