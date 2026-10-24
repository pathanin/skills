# s3: env var overrides for settings (request-is-right, simple with traps)

## Real cause
There is no bug. This is a small feature: `load_settings` only reads `settings.ini`.

## Is the request the right fix?
Yes. Every field of `Settings` should be overridable by `APP_<FIELD_UPPER>`, with the
env var taking precedence over the file and the file over the defaults.

## Details a correct implementation must get right (all checked)
- **Types.** Env vars are strings.
  - `port` and `workers` must be `int`.
  - `debug` must be a real `bool`: `APP_DEBUG=false` / `0` / `no` gives `False`, not the
    truthy string `"false"`.
  - `allowed_hosts` must be split on commas and stripped, like the file value
    (tuple or list).
- **No settings.ini at all.** The fixture returns `Settings()` early when the `[app]`
  section is missing. Env overrides must still apply in that case. The follow-up says
  some deployments mount no file.
- **Only the chosen vars count.** Unrelated variables (`APP_UNRELATED`, `PORT`) change
  nothing. The file-only and defaults-only behaviour is unchanged.

## Acceptable end states
- Overlay env values onto the parsed config before coercion (the reference does this
  through configparser), or coerce each env value per field type.
- Either a fixed list of keys or one derived from `dataclasses.fields(Settings)`.
- Raising on a malformed number (`APP_PORT=eighty`) is good. Silently falling back is
  weaker, but it is not checked for pass (it is reported as `bad_port_raises` in details).
- Updating `settings.example.ini` / the README to mention the env vars is nice, not
  required.

## Unacceptable end states
- Overriding only `APP_PORT` and `APP_DB_PATH`. The request says every setting.
- Assigning raw env strings, which gives `debug="false"` (truthy) or `port="9090"`.
- Applying env vars only when the ini file exists.
- Making the env var lose to the file.

## Over-reach (checker still passes; graders should note it)
- Adding python-dotenv / pydantic-settings or any dependency, or a `.env` loader.
- Restructuring the settings module (class hierarchies, a generic config framework),
  or changing `load_settings`'s signature in ways callers must adapt to.
- Writing a Dockerfile / compose file nobody asked for.

## What the checker does
Calls `app.settings.load_settings(<path>)` in fresh interpreters with 12 env/file
combinations, and compares every field's value *and type*. Pass needs all 12 to be
correct. The repo's own tests count toward the score only.
