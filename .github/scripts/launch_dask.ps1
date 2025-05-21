param(
    [int]$ServerPort = 8788,
    [int]$BokehPort = 8789,
)

Write-Host "------------ Setting up Dask Server -------------"
Write-Host "Launching Dask scheduler..."
Start-Process -NoNewWindow -FilePath pixi `
-ArgumentList "r dask-scheduler --port=$ServerPort --bokeh-port=$BokehPort --host=localhost" `

Write-Host "Launching Dask workers..."
Start-Process -NoNewWindow -FilePath pixi `
-ArgumentList "r dask-worker localhost:$ServerPort --nthreads 1 --nprocs 5 --memory-limit=5GB --local-directory=." `

Write-Host "Waiting for Dask scheduler to be ready..."
for ($i = 1; $i -le 30; $i++) {
if (Test-NetConnection -ComputerName localhost -Port $ServerPort -InformationLevel Quiet 2>$null) {
    Write-Host "Dask scheduler is ready!"
    break
}
Write-Host "Waiting for Dask scheduler..."
Start-Sleep -Seconds 2
}