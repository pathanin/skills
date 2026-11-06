# Stage 2 of the PPTX export (stage 1 = export.py): entrance animations and clip autoplay added through
# PowerPoint itself, then saved with embedded fonts. Called by export.py; can be run alone:
#   powershell -File export_anim.ps1 -in STAGE1.pptx -out FINAL.pptx [-render DIR]
# Animation mirrors deck.js animate(): every shape except a full-slide background enters "With Previous"
# in reading order (top, then left), delay = min(650, (top-50)*0.85 + left*0.08) ms in 1280x720 px.
# Text and small shapes Float In (Ascend) 0.5 s; pictures, clips, big panels and tables Fade 0.6 s.
# Clips play on entry, muted, and loop until the slide changes.
param([Parameter(Mandatory)][string]$in, [Parameter(Mandatory)][string]$out, [string]$render = "")
$ErrorActionPreference = "Stop"
# enum names come from the PIA in the GAC (PowerShell 7 cannot Add-Type it by name)
$pia = Get-ChildItem C:\Windows\assembly\GAC_MSIL\Microsoft.Office.Interop.PowerPoint -Recurse -Filter *.dll -ErrorAction SilentlyContinue | Select-Object -First 1
if (-not $pia) { throw "PowerPoint interop assembly (Microsoft.Office.Interop.PowerPoint) not found in the GAC" }
$asm = [Reflection.Assembly]::LoadFrom($pia.FullName)
$et = $asm.GetType("Microsoft.Office.Interop.PowerPoint.MsoAnimEffect")
$tt = $asm.GetType("Microsoft.Office.Interop.PowerPoint.MsoAnimTriggerType")
# plain ints: enum objects from a reflection-loaded type do not marshal through COM (they arrive as defaults)
$FADE = [int][Enum]::Parse($et, "msoAnimEffectFade"); $ASCEND = [int][Enum]::Parse($et, "msoAnimEffectAscend")
$MEDIAPLAY = [int][Enum]::Parse($et, "msoAnimEffectMediaPlay")
$WITHPREV = [int][Enum]::Parse($tt, "msoAnimTriggerWithPrevious"); $ONCLICK = [int][Enum]::Parse($tt, "msoAnimTriggerOnPageClick")
$app = New-Object -ComObject PowerPoint.Application
$pres = $app.Presentations.Open($in, $false, $false, $false)
$PX = 1280.0 / $pres.PageSetup.SlideWidth      # px per pt (stage is 1280 x 720 px)
$report = @()
try {
  foreach ($sl in $pres.Slides) {
    $seq = $sl.TimeLine.MainSequence
    while ($seq.Count -gt 0) { $seq.Item(1).Delete() }
    $items = @()
    foreach ($sh in $sl.Shapes) {
      $L = $sh.Left * $PX; $Tp = $sh.Top * $PX; $W = $sh.Width * $PX; $H = $sh.Height * $PX
      if ($W -ge 1200 -and $H -ge 650) { continue }                      # background
      $isMedia = ($sh.Type -eq 16)
      $hasText = $sh.HasTextFrame -and $sh.TextFrame2.HasText
      $panel = $isMedia -or $sh.Type -eq 13 -or $sh.HasTable -or ($W * $H -gt 60000 -and -not $hasText)
      $d = [Math]::Min(650, [Math]::Max(0, $Tp - 50) * 0.85 + $L * 0.08)
      $items += [pscustomobject]@{ sh = $sh; d = $d; panel = $panel; media = $isMedia }
    }
    # clips first: AnimationSettings is the legacy API and rewrites any effects already on the slide as plain Appear
    foreach ($it in ($items | Where-Object media)) {
      $ps = $it.sh.AnimationSettings.PlaySettings
      $ps.PlayOnEntry = -1; $ps.LoopUntilStopped = -1; $ps.HideWhileNotPlaying = 0
      try { $it.sh.MediaFormat.Muted = -1 } catch { }
    }
    for ($k = $seq.Count; $k -ge 1; $k--) { if ($seq.Item($k).EffectType -ne $MEDIAPLAY) { $seq.Item($k).Delete() } }
    foreach ($it in ($items | Sort-Object d)) {
      $fx = if ($it.panel) { $FADE } else { $ASCEND }
      $ef = $seq.AddEffect($it.sh, $fx, 0, $WITHPREV)
      $ef.Timing.Duration = if ($it.panel) { 0.6 } else { 0.5 }
      $ef.Timing.TriggerDelayTime = $it.d / 1000.0
    }
    # PlayOnEntry adds its play effect "After Previous" (i.e. after every entrance); start it with the clip's fade instead
    for ($k = 1; $k -le $seq.Count; $k++) {
      $ef = $seq.Item($k)
      if ($ef.EffectType -eq $MEDIAPLAY) {
        $it = $items | Where-Object { $_.sh.Id -eq $ef.Shape.Id } | Select-Object -First 1
        $ef.Timing.TriggerType = $WITHPREV
        $ef.Timing.TriggerDelayTime = $it.d / 1000.0
      }
    }
    # every effect must start on its own (no clicks needed)
    $clicks = 0; for ($k = 1; $k -le $seq.Count; $k++) { if ($seq.Item($k).Timing.TriggerType -eq $ONCLICK) { $clicks++ } }
    $media = @($items | Where-Object media)
    $mediaOk = @($media | Where-Object { $_.sh.AnimationSettings.PlaySettings.PlayOnEntry -eq -1 -and $_.sh.AnimationSettings.PlaySettings.LoopUntilStopped -eq -1 }).Count
    $report += "s{0}: {1} effects, {2} on click, clips {3}/{4} autoplay+loop" -f $sl.SlideIndex, $seq.Count, $clicks, $mediaOk, $media.Count
    if ($render) {
      New-Item -ItemType Directory -Force $render | Out-Null
      $sl.Export((Join-Path $render ("s{0:D2}.png" -f $sl.SlideIndex)), "PNG", 1280, 720)
    }
  }
  $pres.SaveAs($out, 24, -1)          # pptx, embed fonts
} finally {
  $pres.Close(); $app.Quit()
  [System.Runtime.InteropServices.Marshal]::ReleaseComObject($app) | Out-Null
}
$report
