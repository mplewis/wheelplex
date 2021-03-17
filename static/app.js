const oneDaySecs = 60 * 60 * 24;
const options = 8;
const breakAtChars = 20;
const songLength = 4500;

colors = [
  "#f6e58d",
  "#ffbe76",
  "#ff7979",
  "#badc58",
  "#dff9fb",
  "#7ed6df",
  "#e056fd",
  "#686de0",
  "#95afc0",
];

const filters = {
  unwatched: (i) => !i.viewed_at,
  bad_critic: (i) => i.critic_rating && i.critic_rating < 4,
  bad_audience: (i) => i.audience_rating && i.audience_rating < 4,
  disparity: (i) =>
    i.audience_rating &&
    i.critic_rating &&
    i.critic_rating < 4 &&
    i.audience_rating > 6,
};

async function main() {
  const pretoggled = {};
  Object.keys(filters).forEach((k) => (pretoggled[k] = false));

  const app = Vue.createApp({
    data: () => ({
      message: "hello!",
      items: null,
      filters: pretoggled,
      spun: false,
      winner: null,
    }),

    computed: {
      mode() {
        if (!this.items) return "loading";
        if (!this.spun) return "ready";
        if (!this.winner) return "spinning";
        return "done";
      },

      filtered() {
        if (!this.items) return [];
        remaining = this.items.slice();
        Object.entries(this.filters).forEach(([name, enabled]) => {
          if (!enabled) return;
          remaining = remaining.filter((item) => filters[name](item));
        });
        return remaining;
      },
    },

    methods: {
      async spin() {
        this.spun = true;
        const start = buildWheel(this.filtered);
        result = await start();
        this.winner = result;
      },

      spinAgain() {
        this.winner = null;
        this.spin();
      },

      reset() {
        this.spun = false;
        this.winner = null;
      },
    },

    async mounted() {
      await validateSession();
      this.items = await library();
    },
  });

  app.mount("#app");
}

function buildWheel(library) {
  const items = library.slice();
  shuffle(items);
  shuffle(colors);
  const segments = items.slice(0, options).map((item, idx) => ({
    original: item,
    text: multiline(item.title),
    fillStyle: colors[idx],
  }));

  const wheel = new Winwheel({
    textAlignment: "outer",
    pointerAngle: 90,
    pointerGuide: {
      display: true,
      strokeStyle: "black",
      lineWidth: 3,
    },
    numSegments: segments.length,
    segments,
    animation: {
      type: "spinToStop",
      duration: songLength / 1000,
      spins: 6,
    },
  });

  const music = new Audio("fanfare.mp3");

  return function () {
    return new Promise((resolve) => {
      wheel.startAnimation();
      music.play();

      setTimeout(() => {
        return resolve(wheel.getIndicatedSegment().original);
      }, songLength);
    });
  };
}

function shuffle(arr) {
  arr.sort(() => Math.random() - 0.5);
}

function multiline(s) {
  if (s.length <= breakAtChars) return s;
  for (let i = breakAtChars; i > 0; i--) {
    char = s[i];
    breakpoint = !char.match(/[A-Za-z0-9]/);
    if (breakpoint) {
      const first = s.slice(0, i + 1).trim();
      const rest = s.slice(i + 1, s.length);
      return first + "\n" + multiline(rest);
    }
  }
  return s;
}

function epoch() {
  return Number(new Date()) / 1000;
}

async function validateSession() {
  resp = await fetch("/valid", { credentials: "same-origin" });
  if (!resp.ok) {
    window.location.pathname = "/";
  }
}

async function library() {
  const expiry = JSON.parse(localStorage.libraryExpiry);
  if (localStorage.libraryItems && epoch() < expiry) {
    return JSON.parse(localStorage.libraryItems);
  }
  return await populate();
}

async function populate() {
  const resp = await fetch("/list", { credentials: "same-origin" });
  if (!resp.ok) {
    window.location.pathname = "/";
  }
  const data = await resp.json();
  localStorage.libraryItems = JSON.stringify(data);
  localStorage.libraryExpiry = JSON.stringify(epoch() + oneDaySecs);
  return data;
}
