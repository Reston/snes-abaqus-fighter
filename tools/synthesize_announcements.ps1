# Export original, project-authored utterances. This never opens an audio device.
$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Speech
$audioSource = Join-Path $PSScriptRoot '../assets/audio/announcements'
New-Item -ItemType Directory -Force -Path $audioSource | Out-Null
$voiceExport = New-Object System.Speech.Synthesis.SpeechSynthesizer
$voiceExport.SelectVoice('Microsoft Zira Desktop')
$voiceExport.Rate = 3
$voiceExport.Volume = 100
$voiceFormat = New-Object System.Speech.AudioFormat.SpeechAudioFormatInfo(16000, [System.Speech.AudioFormat.AudioBitsPerSample]::Sixteen, [System.Speech.AudioFormat.AudioChannel]::Mono)
foreach ($utterance in @(@('round', 'Round!'), @('fight', 'Fight!'), @('ko', 'K O!'))) {
    $voiceExport.SetOutputToWaveFile((Join-Path $audioSource ($utterance[0] + '.wav')), $voiceFormat)
    $voiceExport.Speak($utterance[1])
    $voiceExport.SetOutputToNull()
}
$voiceExport.Dispose()
