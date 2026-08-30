module Transfer where

sendFile :: FilePath -> IO ()
sendFile path = return ()

data TransferState = Idle | Active

newtype Port = Port Int

class Encoder a where
  encode :: a -> String
