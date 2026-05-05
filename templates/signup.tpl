% rebase("base.tpl", title="Sign up", user=user, error=error, notice=notice)

<section class="auth-card">
  <h1>Create account</h1>
  <form method="post">
    {{!csrf_field()}}
    <input type="hidden" name="next" value="{{next_url}}">
    <label>
      Username
      <input name="username" value="{{username if defined('username') else ''}}" required autocomplete="username" pattern="[a-z0-9][a-z0-9._-]{1,62}">
    </label>
    <label>
      Password
      <input name="password" type="password" required autocomplete="new-password" minlength="8">
    </label>
    <button class="button" type="submit">Sign up</button>
  </form>
  <p class="muted">Already have an account? <a href="/login">Log in</a>.</p>
</section>
