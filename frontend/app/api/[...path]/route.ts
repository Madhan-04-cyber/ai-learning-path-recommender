import { NextRequest, NextResponse } from "next/server";

const backendUrl = process.env.BACKEND_URL || process.env.NEXT_PUBLIC_BACKEND_URL || "";

async function proxy(request: NextRequest, path: string[]) {
	if (!backendUrl) {
		return NextResponse.json(
			{ detail: "Backend URL is not configured." },
			{ status: 500 }
		);
	}

	const targetPath = `/api/${path.join("/")}`;
	const target = new URL(targetPath, backendUrl);
	target.search = request.nextUrl.search;

	const headers = new Headers(request.headers);
	headers.delete("host");

	const init: RequestInit = {
		method: request.method,
		headers,
		redirect: "manual",
	};

	if (request.method !== "GET" && request.method !== "HEAD") {
		init.body = await request.arrayBuffer();
	}

	const response = await fetch(target, init);
	const responseHeaders = new Headers(response.headers);
	responseHeaders.delete("content-encoding");
	responseHeaders.delete("content-length");
	responseHeaders.delete("transfer-encoding");
	responseHeaders.delete("connection");

	return new NextResponse(response.body, {
		status: response.status,
		statusText: response.statusText,
		headers: responseHeaders,
	});
}

export async function GET(request: NextRequest, context: { params: Promise<{ path: string[] }> }) {
	return context.params.then((params) => proxy(request, params.path));
}

export async function POST(request: NextRequest, context: { params: Promise<{ path: string[] }> }) {
	return context.params.then((params) => proxy(request, params.path));
}

export async function PUT(request: NextRequest, context: { params: Promise<{ path: string[] }> }) {
	return context.params.then((params) => proxy(request, params.path));
}

export async function PATCH(request: NextRequest, context: { params: Promise<{ path: string[] }> }) {
	return context.params.then((params) => proxy(request, params.path));
}

export async function DELETE(request: NextRequest, context: { params: Promise<{ path: string[] }> }) {
	return context.params.then((params) => proxy(request, params.path));
}

export async function OPTIONS(request: NextRequest, context: { params: Promise<{ path: string[] }> }) {
	return context.params.then((params) => proxy(request, params.path));
}
