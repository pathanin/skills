# Render slides of any .pptx through PowerPoint to OUT/sNN.png (1280x720), and list text that overflows its box.
#   powershell -File render_pptx.ps1 -deck DECK.pptx -out DIR [-list 1,4,7]
# Used to compare a conversion (init_deck.py --from) with how PowerPoint draws the source deck.
param([Parameter(Mandatory)][string]$deck, [Parameter(Mandatory)][string]$out, [string]$list = "")
$ErrorActionPreference = "Stop"
New-Item -ItemType Directory -Force $out | Out-Null
$app = New-Object -ComObject PowerPoint.Application
$pres = $app.Presentations.Open((Resolve-Path $deck).Path, $true, $false, $false)
try {
  $nums = if ($list) { $list.Split(",") | ForEach-Object { [int]$_ } } else { 1..$pres.Slides.Count }
  $rep = @()
  function Chk($sh, $k) {
    if ($sh.Type -eq 6) { foreach ($g in $sh.GroupItems) { Chk $g $k }; return }
    if ($sh.HasTextFrame -and $sh.TextFrame2.HasText) {
      $tr = $sh.TextFrame2.TextRange
      if ($tr.BoundHeight -gt $sh.Height + 2) {
        $script:rep += "s{0} [{1}] text {2:N0} pt tall in a {3:N0} pt box: {4}" -f $k, $sh.Name, $tr.BoundHeight, $sh.Height, ($tr.Text -replace "\r", " | ").Substring(0, [Math]::Min(60, $tr.Text.Length))
      }
    }
  }
  foreach ($k in $nums) {
    $sl = $pres.Slides.Item($k)
    foreach ($sh in $sl.Shapes) { Chk $sh $k }
    $sl.Export((Join-Path $out ("s{0:D2}.png" -f $k)), "PNG", 1280, 720)
  }
  "rendered $($nums.Count) of $($pres.Slides.Count) slides to $out"
  $rep
} finally {
  $pres.Close(); $app.Quit()
  [System.Runtime.InteropServices.Marshal]::ReleaseComObject($app) | Out-Null
}
