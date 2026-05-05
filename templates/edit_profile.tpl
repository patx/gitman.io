% rebase("base.tpl", title="Edit profile", user=user, error=error, notice=notice)

<section class="auth-card wide">
  <h1>Edit profile</h1>
  <form method="post">
    {{!csrf_field()}}
    <label>
      Display name
      <input name="display_name" value="{{profile['display_name']}}" maxlength="80">
    </label>
    <label>
      Bio
      <textarea name="bio" rows="6" maxlength="1000">{{profile["bio"]}}</textarea>
    </label>
    <label>
      Website
      <input name="website" value="{{profile['website']}}" placeholder="https://example.com" maxlength="255">
    </label>
    <button class="button" type="submit">Save profile</button>
  </form>
  <br><br>
  <p class="muted"><a href="/{{profile['username']}}"><- Back</a></p>
</section>
