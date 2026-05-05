% rebase("base.tpl", title="Log in", user=user, error=error, notice=notice)

<section class="auth-card">
  <h1>Log in</h1>
  <form method="post">
    {{!csrf_field()}}
    <input type="hidden" name="next" value="{{next_url}}">
    <label>
      Username
      <input name="username" value="{{username if defined('username') else ''}}" required autocomplete="username">
    </label>
    <label>
      Password
      <input name="password" type="password" required autocomplete="current-password">
    </label>
    <button class="button" type="submit">Log in</button>
  </form>
  <p class="muted">Need an account? <a href="/signup">Sign up</a>.</p>
</section>
